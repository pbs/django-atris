pip install --upgrade pip
pip install -r test_requirements.txt
pip install -e .
django-admin startproject website
cd website
cp -r ../src/atris atris
cp -r ../tests tests
mv tests/settings_override.py website
python manage.py makemigrations --settings=website.settings_override
python manage.py migrate --settings=website.settings_override
cp -r ./atris/migrations ../src/atris
cp -r ./tests/migrations ../tests
pytest --ds=website.settings_override -vv --html=../test-results.html --self-contained-html --cov=./atris --cov-report=term-missing:skip-covered tests/tests
cd ..
rm -rf website
