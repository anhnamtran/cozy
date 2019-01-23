export PYTHONUNBUFFERED=1

set -e

OUT_DIR="/tmp/cozy-logs"

# $1: exp name
# $2: out name
function run_exp {
  redis-cli FLUSHALL
  pushd cache_examples

  echo "Running Cozy with no cache"
  { time cozy --no-cost-model-cache $1.ds --java $2.java &> $OUT_DIR/$1-no-cache.log ; } &> $1-no-cache.time

  run_driver $1 $2

  echo "Running Cozy with cache"
  { time cozy $1.ds --java $2.java &> $OUT_DIR/$1-cache.log ; } &> $1-cache.time

  run_driver $1 $2

  popd
}

# $1: exp name
# $2: driver name
function run_driver {
  rm -rf *.class
  javac -cp .:* *.java

  java $2Main
}

mkdir -p $OUT_DIR

run_exp maxbag MaxBag
