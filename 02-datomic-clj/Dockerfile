# Datomic Pro (free, Apache-2.0 since 2023): a transactor with dev storage, for a REPL on the host.
FROM eclipse-temurin:21-jre
ARG DATOMIC_VERSION=1.0.7745
RUN apt-get update && apt-get install -y --no-install-recommends curl unzip && rm -rf /var/lib/apt/lists/* \
 && curl -fsSL -o /tmp/datomic.zip \
      https://datomic-pro-downloads.s3.amazonaws.com/${DATOMIC_VERSION}/datomic-pro-${DATOMIC_VERSION}.zip \
 && unzip -q /tmp/datomic.zip -d /opt && mv /opt/datomic-pro-${DATOMIC_VERSION} /opt/datomic && rm /tmp/datomic.zip
WORKDIR /opt/datomic
COPY transactor.properties config/
EXPOSE 4334 4335
CMD ["bin/transactor", "config/transactor.properties"]
