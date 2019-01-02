#!/bin/bash
export PYTHONUBUFFERED=1

set -e

trap "exit 1" SIGINT

EXP_OUT="${PWD}/exp_out"

CACHE="${EXP_OUT}/cache"
NO_CACHE="${EXP_OUT}/no_cache"

SUMMARY="${EXP_OUT}/summary.txt"

WARM_UP_LIMIT=3
if [ $# -eq 2 ]; then
  WARM_UP_LIMIT=$2
fi

TIME_OUT=$1
if [ $# -eq 0 ]; then
  TIME_OUT=60
fi

function run_exp {
  echo "Flushing Cache"
  redis-cli FLUSHALL
  COUNTER=0

  echo "------------------------------------------"
  echo "------------------------------------------"
  echo "Running baseline on $1"
  echo "Run no. $COUNTER"
  pushd examples > /dev/null
  cozy $1.ds -t $TIME_OUT --no-cost-model-cache > "${NO_CACHE}/$1.txt"
  popd

  ./vis.py $1 $COUNTER
  let COUNTER=COUNTER+1

  echo "$1.ds:" >> $SUMMARY
  tail -n 1 < "${NO_CACHE}/$1.txt" >> $SUMMARY

  echo "------------------------------------------"
  echo "Cache warmup limit: $WARM_UP_LIMIT"
  while [ $COUNTER -le $WARM_UP_LIMIT ]; do
    echo "------------------------------------------"
    echo "Run no. $COUNTER"

    pushd examples > /dev/null
    cozy $1.ds -t $TIME_OUT > "${CACHE}/$1-$COUNTER.txt"
    popd

    update_summary $1 $COUNTER

    ./vis.py $1 $COUNTER
    cp "examples/data.txt" "plots/$1/run-$1.txt"

    let COUNTER=COUNTER+1
  done
}

function update_summary {
  tail -n 1 < "${CACHE}/$1-$2.txt" >> $SUMMARY

  echo
}

mkdir -p $CACHE
mkdir -p $NO_CACHE

> $SUMMARY

run_exp maxbag
run_exp tpchq5
#run_exp clausedb
run_exp nested-map
run_exp disjunction
run_exp graph
run_exp map
