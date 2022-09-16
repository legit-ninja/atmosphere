import base64

import pykube
import yaml
from schematics import types
from schematics.transforms import blacklist

from atmosphere.models import base
from atmosphere.models.openstack_helm import endpoints, images, monitoring


class Values(base.Model):
    chart = types.StringType(required=True)

    endpoints = types.ModelType(endpoints.Endpoints)
    images = types.ModelType(images.Images)
    monitoring = types.ModelType(monitoring.Monitoring)

    class Options:
        roles = {"default": blacklist("chart")}

    @classmethod
    def for_chart(cls, chart, config):
        return cls(
            {
                "chart": chart,
                "endpoints": endpoints.Endpoints.for_chart(chart, config),
                "images": images.Images.for_chart(chart, config),
                "monitoring": monitoring.Monitoring.for_chart(chart, config),
            }
        )

    def secret(self):
        values = yaml.dump(self.to_native(), default_flow_style=False)

        return {
            "apiVersion": "v1",
            "kind": "Secret",
            "metadata": {
                "name": f"atmosphere-{self.chart}",
                "namespace": "openstack",
            },
            "data": {
                "values.yaml": base64.b64encode(values.encode("utf-8")).decode("utf-8"),
            },
        }

    def apply(self, api):
        resource = self.secret()
        secret = pykube.Secret(api, resource)

        if not secret.exists():
            secret.create()

        if secret.obj["data"] != resource["data"]:
            secret.obj["data"] = resource["data"]
            secret.update()