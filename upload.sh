
python3.8 setup.py sdist build
twine upload ./dist/*

rm -rf ./dist
rm -rf ./build
rm -rf ./wintersweet.egg-info
