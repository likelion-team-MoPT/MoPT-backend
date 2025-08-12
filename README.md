초기세팅 방법

git clone https://github.com/likelion-team-MoPT/MoPT-backend.git

cd MoPT-backend

poetry install

poetry lock

eval $(poetry env activate)

pre-commit install

python manage.py runserver
