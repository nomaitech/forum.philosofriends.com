## Deployment note

Always deploy using the local Helm chart and values file so persistence, env vars (ALLOWED_HOSTS/CSRF), and uvicorn/asgi are enabled:

1) Build and push the image to `pdr.jonbesga.com`.
2) Deploy with:
   `helm upgrade --install forum deploy/web-app -n jon -f deploy/philo-news-values.yaml --set image.name=<image>:<tag> --set ingress.host=forum.philosofriends.com`
