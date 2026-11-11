# Local development storage, built from the upstream source-only release.
FROM golang:1.24.8-bookworm AS build
ENV CGO_ENABLED=0 GOTOOLCHAIN=local
RUN go install github.com/minio/minio@RELEASE.2025-10-15T17-29-55Z
RUN mkdir /data && cp /go/pkg/mod/github.com/minio/minio@*/LICENSE /LICENSE

FROM scratch
COPY --from=build /go/bin/minio /minio
COPY --from=build /etc/ssl/certs/ca-certificates.crt /etc/ssl/certs/ca-certificates.crt
COPY --from=build /LICENSE /LICENSE
COPY --from=build --chown=10001:10001 /data /data
USER 10001:10001
ENTRYPOINT ["/minio"]
CMD ["server", "/data"]
