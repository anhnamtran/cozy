from collections import defaultdict, OrderedDict
import datetime
import itertools
import functools
import sys
import traceback

from cozy.target_syntax import *
from cozy.typecheck import is_collection
from cozy.syntax_tools import subst, pprint, free_vars, free_funcs, fresh_var, alpha_equivalent, enumerate_fragments, strip_EStateVar, freshen_binders
from cozy.wf import ExpIsNotWf, exp_wf
from cozy.common import OrderedSet, ADT, Visitor, fresh_name, unique, pick_to_sum, cross_product, OrderedDefaultDict, OrderedSet, group_by, find_one, extend, StopException
from cozy.solver import satisfy, satisfiable, valid, IncrementalSolver
from cozy.evaluation import eval, eval_bulk, mkval, construct_value, uneval, eq
from cozy.cost_model import CostModel, Order, rt as runtime, asymptotic_runtime, max_storage_size, find_case_where_better, LINEAR_TIME_UOPS
from cozy.opts import Option
from cozy.pools import ALL_POOLS, RUNTIME_POOL, STATE_POOL, pool_name
from cozy.enumeration import Enumerator, fingerprint
from cozy.contexts import Context, shred, replace
from cozy.logging import task, event

from .acceleration import try_optimize

eliminate_vars = Option("eliminate-vars", bool, False)
incremental = Option("incremental", bool, False, description="Experimental option that can greatly improve performance.")

class NoMoreImprovements(Exception):
    pass

class Learner(object):
    def __init__(self, target, assumptions, context, examples, cost_model, stop_callback, hints):
        self.context = context
        self.stop_callback = stop_callback
        self.cost_model = cost_model
        self.assumptions = assumptions
        self.hints = list(hints)
        self.reset(examples)
        self.watch(target)

    def reset(self, examples):
        self.examples = list(examples)

    def watch(self, new_target):
        self.target = new_target

    def matches(self, fp, target_fp):
        assert isinstance(fp[0], Type)
        assert isinstance(target_fp[0], Type)
        if fp[0] != target_fp[0]:
            return False
        t = fp[0]
        return all(eq(t, fp[i], target_fp[i]) for i in range(1, len(fp)))

    def next(self):
        class No(object):
            def __init__(self, msg):
                self.msg = msg
            def __bool__(self):
                return False
            def __str__(self):
                return "no: {}".format(self.msg)
        # with task("pre-computing cardinalities"):
        #     cards = [self.cost_model.cardinality(ctx.e) for ctx in enumerate_fragments(self.target) if is_collection(ctx.e.type)]
        def check_wf(e, ctx, pool):
            with task("checking well-formedness", size=e.size()):
                try:
                    exp_wf(e, pool=pool, context=ctx, assumptions=self.assumptions)
                except ExpIsNotWf as exc:
                    return No("at {}: {}".format(pprint(exc.offending_subexpression), exc.reason))
                if pool == RUNTIME_POOL and self.cost_model.compare(e, self.target, ctx, pool) not in (Order.LT, Order.EQUAL):
                    # from cozy.cost_model import debug_comparison
                    # debug_comparison(self.cost_model, e, self.target, ctx)
                    return No("too expensive")
                # if isinstance(e.type, TBag):
                #     c = self.cost_model.cardinality(e)
                #     if all(cc < c for cc in cards):
                #         # print("too big: {}".format(pprint(e)))
                #         return No("too big")
                return True

        root_ctx = self.context
        frags = list(unique(itertools.chain(
            shred(self.target, root_ctx),
            *[shred(h, root_ctx) for h in self.hints])))
        enum = Enumerator(
            examples=self.examples,
            cost_model=self.cost_model,
            check_wf=check_wf,
            hints=frags,
            heuristics=try_optimize,
            stop_callback=self.stop_callback)

        size = 0
        # target_cost = self.cost_model.cost(self.target, RUNTIME_POOL)
        target_fp = fingerprint(self.target, self.examples)

        if not hasattr(self, "blacklist"):
            self.blacklist = set()

        while True:

            print("starting minor iteration {} with |cache|={}".format(size, enum.cache_size()))
            if self.stop_callback():
                raise StopException()

            n = 0
            for (e, ctx, pool) in shred(self.target, root_ctx):
                with task("checking substitutions",
                        target=pprint(replace(self.target, root_ctx, RUNTIME_POOL, e, ctx, pool, EVar("___"))),
                        e=pprint(e)):
                    for info in enum.enumerate_with_info(size=size, context=ctx, pool=pool):
                        with task("checking substitution", expression=pprint(info.e)):
                            if self.stop_callback():
                                raise StopException()
                            if info.e.type != e.type:
                                event("wrong type")
                                continue
                            if alpha_equivalent(info.e, e):
                                event("no change")
                                continue

                            k = (e, ctx, pool, info.e)
                            if k in self.blacklist:
                                event("blacklisted")
                                continue

                            n += 1
                            ee = freshen_binders(replace(
                                self.target, root_ctx, RUNTIME_POOL,
                                e, ctx, pool,
                                info.e), root_ctx)
                            if not self.matches(fingerprint(ee, self.examples), target_fp):
                                event("incorrect")
                                self.blacklist.add(k)
                                continue
                            wf = check_wf(ee, root_ctx, RUNTIME_POOL)
                            if not wf:
                                event("not well-formed [wf={}]".format(wf))
                                # if "expensive" in str(wf):
                                #     print(repr(self.cost_model.examples))
                                #     print(repr(ee))
                                self.blacklist.add(k)
                                continue
                            if self.cost_model.compare(ee, self.target, root_ctx, RUNTIME_POOL) != Order.LT:
                                event("not an improvement")
                                self.blacklist.add(k)
                                continue
                            print("FOUND A GUESS AFTER {} CONSIDERED".format(n))
                            return ee

            print("CONSIDERED {}".format(n))
            size += 1

        raise NoMoreImprovements()

def can_elim_vars(spec : Exp, assumptions : Exp, vs : [EVar]):
    spec = strip_EStateVar(spec)
    sub = { v.id : fresh_var(v.type) for v in vs }
    return valid(EImplies(
        EAll([assumptions, subst(assumptions, sub)]),
        EEq(spec, subst(spec, sub))))

_DONE = set([EVar, EEnumEntry, ENum, EStr, EBool, EEmptyList, ENull])
def heuristic_done(e : Exp):
    return (
        (type(e) in _DONE) or
        (isinstance(e, ESingleton) and heuristic_done(e.e)) or
        (isinstance(e, EStateVar) and heuristic_done(e.e)) or
        (isinstance(e, EGetField) and heuristic_done(e.e)) or
        (isinstance(e, EUnaryOp) and e.op not in LINEAR_TIME_UOPS and heuristic_done(e.e)) or
        (isinstance(e, ENull)))

def never_stop():
    return False

def improve(
        target        : Exp,
        context       : Context,
        assumptions   : Exp            = T,
        stop_callback                  = never_stop,
        hints         : [Exp]          = (),
        examples      : [{str:object}] = ()):
    """
    Improve the target expression using enumerative synthesis.
    This function is a generator that yields increasingly better and better
    versions of the input expression `target`.

    Notes on internals of this algorithm follow.

    Key differences from "regular" enumerative synthesis:
        - Expressions are either "state" expressions or "runtime" expressions,
          allowing this algorithm to choose what things to store on the data
          structure and what things to compute at query execution time. (The
          cost model is ultimately responsible for this choice.)
        - If a better version of *any subexpression* for the target is found,
          it is immediately substituted in and the overall expression is
          returned. This "smooths out" the search space a little, and lets us
          find kinda-good solutions very quickly, even if the best possible
          solution is out of reach.
    """

    print("call to improve:")
    print("""improve(
        target={target!r},
        context={context!r},
        assumptions={assumptions!r},
        stop_callback={stop_callback!r},
        hints={hints!r},
        examples={examples!r})""".format(
            target=target,
            context=context,
            assumptions=assumptions,
            stop_callback=stop_callback,
            hints=hints,
            examples=examples))

    target = freshen_binders(target, context)
    assumptions = freshen_binders(assumptions, context)

    print()
    print("improving: {}".format(pprint(target)))
    print("subject to: {}".format(pprint(assumptions)))
    print()

    try:
        assert exp_wf(target, context=context, assumptions=assumptions)
    except ExpIsNotWf as ex:
        print("WARNING: initial target is not well-formed [{}]; this might go poorly...".format(str(ex)))
        print(pprint(ex.offending_subexpression))
        print(pprint(ex.offending_subexpression.type))
        # raise

    state_vars = [v for (v, p) in context.vars() if p == STATE_POOL]
    if eliminate_vars.value and can_elim_vars(target, assumptions, state_vars):
        print("This job does not depend on state_vars.")
        # TODO: what can we do about it?

    hints = [freshen_binders(h, context) for h in hints] + [target]
    vars = list(v for (v, p) in context.vars())
    funcs = free_funcs(EAll([assumptions] + hints)) # TODO: context should know this

    solver = None
    if incremental.value:
        solver = IncrementalSolver(vars=vars, funcs=funcs)
        solver.add_assumption(assumptions)
        _sat = solver.satisfy
    else:
        _sat = lambda e: satisfy(e, vars=vars, funcs=funcs)

    if _sat(T) is None:
        print("assumptions are unsat; this query will never be called")
        yield construct_value(target.type)
        return

    examples = list(examples)
    cost_model = CostModel(funcs=funcs, assumptions=assumptions)
    learner = Learner(target, assumptions, context, examples, cost_model, stop_callback, hints)
    try:
        while True:
            # 1. find any potential improvement to any sub-exp of target
            try:
                new_target = learner.next()
            except NoMoreImprovements:
                break
            print("Found candidate improvement: {}".format(pprint(new_target)))

            # 2. check
            with task("verifying candidate"):
                if incremental.value:
                    solver.push()
                    solver.add_assumption(ENot(EBinOp(target, "==", new_target).with_type(BOOL)))
                    counterexample = _sat(T)
                else:
                    formula = EAll([assumptions, ENot(EBinOp(target, "==", new_target).with_type(BOOL))])
                    counterexample = _sat(formula)
            if counterexample is not None:
                if counterexample in examples:
                    print("assumptions = {!r}".format(assumptions))
                    print("duplicate example: {!r}".format(counterexample))
                    print("old target = {!r}".format(target))
                    print("new target = {!r}".format(new_target))
                    print("old fp = {}".format(learner._fingerprint(old_e)))
                    print("new fp = {}".format(learner._fingerprint(new_e)))
                    print("old target fp = {}".format(learner._fingerprint(target)))
                    print("new target fp = {}".format(learner._fingerprint(new_target)))
                    raise Exception("got a duplicate example")
                # a. if incorrect: add example, reset the learner
                examples.append(counterexample)
                event("new example: {!r}".format(counterexample))
                print("wrong; restarting with {} examples".format(len(examples)))
                learner.reset(examples)
            else:
                # b. if correct: yield it, watch the new target, goto 1
                print("The replacement is valid!")
                print("Confirming cost...")
                with task("verifying cost"):
                    cost_cex = find_case_where_better(target, new_target, vars=vars, funcs=funcs)
                    if cost_cex is None:
                        print("Yep, it's an improvement!")
                        yield new_target
                    else:
                        print("Nope, it isn't better!")
                        cost_model.add_example(cost_cex)
                        new_target = target

                # if reset_on_success.value and (not check_final_cost.value or ordering != Cost.UNORDERED):
                learner.reset(examples)
                learner.watch(new_target)
                target = new_target

                if heuristic_done(new_target):
                    print("target now matches doneness heuristic")
                    break
            if incremental.value:
                solver.pop()

    except KeyboardInterrupt:
        raise
