#!/bin/bash
export PYTHONUBUFFERED=1

set -e

EXP_OUT="${PWD}/exp_out"

CACHE="${EXP_OUT}/cache"
NO_CACHE="${EXP_OUT}/no_cache"

SUMMARY="${EXP_OUT}/summary.log"

TIME_OUT=$1
if [ $# -eq 0 ]; then
  TIME_OUT=60
fi

function run_exp {
  cozy $1.ds -t $TIME_OUT --no-cost-model-cache | tee "${NO_CACHE}/$1.log"
  cozy $1.ds -t $TIME_OUT | tee "${CACHE}/$1.log"

  update_summary $1
}

function update_summary {
  echo "$1.ds:" >> $SUMMARY
  tail -n 1 < "${NO_CACHE}/$1.log" >> $SUMMARY
  tail -n 1 < "${CACHE}/$1.log" >> $SUMMARY

  echo
}

mkdir -p $CACHE
mkdir -p $NO_CACHE

> $SUMMARY

pushd examples > /dev/null

run_exp maxbag
run_exp tpchq5
run_exp clausedb
run_exp nested-map
run_exp disjunction
run_exp graph
run_exp map
