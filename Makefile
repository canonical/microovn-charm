CHARMS := microovn-control microovn-worker

build: $(CHARMS)

$(CHARMS):
	$(MAKE) -C $@

clean:
	$(MAKE) -C microovn-control clean
	$(MAKE) -C microovn-worker clean
