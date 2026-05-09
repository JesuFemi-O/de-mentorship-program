FROM quay.io/debezium/connect:3.5

ENV PLUGIN_DIR=/kafka/connect
ENV AVRO_CONVERTER_VERSION=7.7.1
ENV S3_SINK_CONNECTOR_VERSION=10.5.23

USER root

RUN curl -L -o /tmp/avro.zip \
      https://hub-downloads.confluent.io/api/plugins/confluentinc/kafka-connect-avro-converter/versions/$AVRO_CONVERTER_VERSION/confluentinc-kafka-connect-avro-converter-$AVRO_CONVERTER_VERSION.zip && \
    unzip -q /tmp/avro.zip -d $PLUGIN_DIR/ && \
    rm /tmp/avro.zip

RUN curl -L -o /tmp/s3.zip \
      https://hub-downloads.confluent.io/api/plugins/confluentinc/kafka-connect-s3/versions/$S3_SINK_CONNECTOR_VERSION/confluentinc-kafka-connect-s3-$S3_SINK_CONNECTOR_VERSION.zip && \
    unzip -q /tmp/s3.zip -d $PLUGIN_DIR/ && \
    rm /tmp/s3.zip

USER kafka
