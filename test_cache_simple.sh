export PYTHONUNBUFFERED=1

set -x

OUT_DIR="/tmp/cozy-logs"

# $1: exp name
# $2: out name
function run_exp {
  pushd cache_examples

  { time cozy --no-cost-model-cache $1.ds --java $2.java &> $OUT_DIR/$1.log ; } &> $1-no-cache.time

  run_driver $1 $2

  { time cozy $1.ds --java $1.java &> $OUT_DIR/$1.log ; } &> $1-cache.time

  run_driver $1 $2

  popd
}

# $1: exp name
# $2: driver name
function run_driver {
  javac -cp .:* *.java

  java $2Main
}

mkdir $OUT_DIR

run_exp maxbag MaxBag
