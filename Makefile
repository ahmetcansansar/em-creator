all: .PHONY

du-h: .PHONY
	du -h --max-depth=1 | tee du-h

install_mg5:
	$(shell [ -x "mg5.tar.gz" ] || {wget http://www.hephy.at/user/wwaltenberger/dist/mg5.tar.gz; }; )
	rm -rf mg5.old
	$(shell [ -x "mg5" ] && { mv -f mg5 mg5.old; } )
	tar xzvf mg5.tar.gz 

install_ma5:
	$(shell [ -x "ma5.tar.gz" ] || { wget https://smodels.github.io/downloads/tarballs/ma5.tar.gz; }; )
	rm -rf ma5.old
	$(shell [ -x "ma5" ] && { mv -f ma5.template ma5.old; } )
	tar xzvf ma5.tar.gz 

backup_embaked:
	./utils/backupEmbaked.py

.PHONY:
