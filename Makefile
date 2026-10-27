build:
	gftools builder sources/config.yaml

test:
	fontbakery check-googlefonts -l WARN fonts/variable/*.ttf

clean:
	rm -rf fonts
