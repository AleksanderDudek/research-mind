FROM bitnami/spark:3.5

USER root

RUN pip install --no-cache-dir \
    pypdf==4.3.1 \
    qdrant-client==1.9.1 \
    sentence-transformers==3.3.1 \
    requests==2.32.3 \
    python-dotenv==1.0.1

USER 1001

WORKDIR /opt/bitnami/spark

COPY jobs/ /opt/spark-jobs/
