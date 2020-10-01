all: .PHONY

du-h:
	du -h --max-depth=1 | tee du-h

install_mg5:
	wget http://www.hephy.at/user/wwaltenberger/dist/mg5.tar.gz
	rm -rf mg5.old
	mv -f mg5 mg5.old
	tar xzvf mg5.tar.gz 

install_ma5:
	wget https://smodels.github.io/downloads/tarballs/ma5.tar.gz
	rm -rf ma5.old
	mv -f ma5.template ma5.old
	tar xzvf ma5.tar.gz 

.PHONY:
