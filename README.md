# hint-web

Web application for HINT

# Setup the development environment

If developing the backend, the easiest is to download all the required files, 
and the run:

```bash
docker compose -f docker-compose.dev.yml up
```

Once all the containers are up, run:

```bash
docker compose exec hint python manage.py makemigrations
docker compose exec hint python manage.py migrate
docker compose exec hint python manage.py load_data
docker compose restart hint
```

and you should be able to access hint at http://localhost

If you're developing the front-end, you need to,
[install node](https://nodejs.org/en/learn/getting-started/how-to-install-nodejs)
and also
[install Tailwind](https://tailwindcss.com/docs/installation). Also, please
read the [htmx documentation](https://htmx.org), as HINT does not rely on
React-style JavaScript frameworks. If you're attempting to change the network
visualization template, please have a look at
[cytoscape.js's documentation](https://js.cytoscape.org)

```bash
docker compose exec hint bash
npx tailwindcss -i ./base/static/css/input.css -o ./base/static/css/output.css --watch
```

and follow Tailwind's instructions. This needs to be done everytime the
container restarts though, so it may make more sense to rebuild the entrypoint
of the `hint` service to run Django's development server rather than guinicorn.
If you don't know what this means, please read [here](https://docs.djangoproject.com/en/5.0/intro/tutorial01/#the-development-server)
and [here](https://docs.docker.com/compose/compose-file/05-services/#command).
