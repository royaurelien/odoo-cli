FROM odoo:17.0

USER root

# RUN apt-get update && apt-get install -y --no-install-recommends git ssh

RUN python3 -m pip install \
    manifestoo \
    inotify \
    pre-commit \
    coverage \
    websocket-client \
    pytest-odoo \
    poetry \
    ipykernel

RUN mkdir /workspace && chown odoo:odoo /workspace -R

USER odoo
