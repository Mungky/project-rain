# Custom SearXNG image that bakes Rain's settings.yml into the image.
#
# Why: on Coolify the `./searxng:/etc/searxng` bind mount was getting seeded
# with the image's DEFAULT settings (limiter on, formats: [html] only), so our
# limiter:false + json config never applied and JSON search returned 403.
# Baking the file into the image guarantees it loads regardless of volume quirks.
FROM searxng/searxng:latest

COPY settings.yml /etc/searxng/settings.yml
