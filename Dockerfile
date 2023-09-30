FROM python:3.11

WORKDIR /

RUN git clone https://github.com/Weaselcore/bear_bot_2.git
RUN pip install pipenv
RUN apt update
RUN apt -y install ffmpeg
WORKDIR /bear_bot_2
RUN pipenv install --deploy --ignore-pipfile

CMD [ "pipenv", "run", "python", "bot.py" ]
