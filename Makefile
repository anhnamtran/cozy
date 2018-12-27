TIMEOUT=300
CACHE_LIMIT=5
RM=rm -rf
EMAIL=atran35@cs.washington.edu

all: update clean test-cache notify

update: cozy requirements.txt
	git pull > /dev/null
	pip install . > /dev/null

test-cache: test_cache.sh
	-./test_cache.sh ${TIMEOUT} ${CACHE_LIMIT} && ([ $$? -eq 0 ] && (printf "Subject: test_cache done\nSucess\n" > response.txt)) || (printf "Subject: test_cache done\nFailure\n" > response.txt)  

notify: response.txt
	sendmail ${EMAIL} < response.txt

clean:
	${RM} plots
	${RM} exp_out
	${RM} examples/data.txt
	${RM} response.txt
