ARG IMAGE=alpine:3.22

FROM $IMAGE AS image

WORKDIR /testing
COPY verify.sh /verify.sh
ENTRYPOINT /verify.sh
