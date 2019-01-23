export PYTHONUNBUFFERED=1

set -e

LOG_DIR="/tmp/cozy-logs"

OUT_DIR="$LOG_DIR/cozy"
TIME_DIR="$LOG_DIR/times"

# $1: exp name
# $2: out name
function run_exp {
  redis-cli FLUSHALL
  pushd cache_examples > /dev/null

  echo "Running Cozy with no cache"
  { time cozy --no-cost-model-cache $1.ds --java $2.java &> $OUT_DIR/$1-no-cache.log ; } &> $TIME_DIR/$1-no-cache.time

  run_driver $1 $2

  echo "Running Cozy with cache"
  { time cozy $1.ds --java $2.java &> $OUT_DIR/$1-cache.log ; } &> $TIME_DIR/$1-cache.time

  run_driver $1 $2

  popd > /dev/null

  echo "----------------------------------------------------------------------"
}

# $1: exp name
# $2: driver name
function run_driver {
  rm -rf *.class
  javac -cp .:* *.java

  java $2Main
}

mkdir -p $OUT_DIR
mkdir -p $TIME_DIR

run_exp maxbag MaxBag
