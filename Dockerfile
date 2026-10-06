FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml README.md LICENSE THIRD-PARTY-NOTICES.md ./
COPY src ./src
RUN pip install --no-cache-dir . && useradd --uid 10001 --create-home app
ENV XIAOMI_S400_SESSION=/home/app/.config/xiaomi-s400/session.json
USER app
EXPOSE 8080
ENTRYPOINT ["xiaomi-s400"]
CMD ["serve", "--host", "0.0.0.0"]
