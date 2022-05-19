FROM python:3.10

RUN \
        python -m pip install pyyaml bottle \
    &&  mkdir app && mkdir /app/server

COPY LICENSE    /app/server/
COPY *.py       /app/server/
COPY *.html     /app/server/
COPY Demo       /app/server/Demo

ARG UID=1000
ARG GID=1000
ARG PWD=2OYyoafdd2RFtSB8L1y
ARG UNAME=yaml4schm

RUN  groupadd -g ${GID} ${UNAME} \
  && useradd -m -u ${UID} -g ${GID} ${UNAME} \
  && echo "${UNAME}:${PWD}" | chpasswd

WORKDIR /app/server

USER ${UNAME}

ENTRYPOINT [ "python" ]
CMD [ "/app/server/server.py" ]
