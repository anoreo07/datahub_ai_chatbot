FROM nginx:stable-alpine AS runner

RUN addgroup -S appgroup && adduser -S appuser -G appgroup

COPY datahub-ai-chatbot/app/static /usr/share/nginx/html
COPY deploy/nginx/nginx.conf /etc/nginx/nginx.conf

RUN chown -R appuser:appgroup /usr/share/nginx/html /etc/nginx && \
    chmod -R 644 /usr/share/nginx/html/* && \
    chmod -R 644 /etc/nginx/nginx.conf

EXPOSE 80

USER appuser

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD wget -qO- http://localhost:80/health || exit 1

CMD ["nginx", "-g", "daemon off;"]
