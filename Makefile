all: .PHONY

du-h: .PHONY
	du -h --max-depth=1 | tee du-h.temp
	mv du-h.temp du-h

install_mg5:
	test -e mg5 || cp -r mg5.template mg5
	cd mg5; make.py

install_ma5:
	test -e ma5 || cp -r ma5.template ma5
	cd ma5; make.py

install_cm2:
	test -e hepmc2 || cp -r hepmc2.template hepmc2
	cd hepmc2; make.py
	test -e cm2 || cp -r cm2.template cm2
	cd cm2; make.py

pull_from_clip:
	mkdir -p embaked
	scp -r clip-login-1:git/em-creator/embaked/\*embaked embaked

backup_embaked:
	./utils/backupEmbaked.py

.PHONY:
