FROM jumpssh/image_sshd:latest

RUN apk add --update \
    python3 \
    py3-pip \
  && pip install --upgrade pip \
  && pip install flask -U \
  && rm -rf /var/cache/apk/* \
  && adduser -D app \
  && mkdir /restserver  \
  && chown -R app:app /restserver

USER app

# add directly the jar
ADD app.py /restserver/app.py

CMD python3 /restserver/app.py

EXPOSE 5000
