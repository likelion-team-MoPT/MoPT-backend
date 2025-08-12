초기세팅 방법

git clone https://github.com/likelion-team-MoPT/MoPT-backend.git

cd MoPT-backend

poetry install


pyproject.toml changed significantly since poetry. lock was last generated. Run poetry lock to fix the lock file.
(이 표시가 뜨면 poetry lock 안뜨면 생략)


eval $(poetry env activate)

pre-commit install

python manage.py runserver
