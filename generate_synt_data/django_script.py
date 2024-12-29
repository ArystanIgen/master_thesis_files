import json
from dataclasses import dataclass

from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand

from apps.accounts.factories import UserFactory
from apps.common.text_choices import GroupCodes, UserStatuses
from apps.discovery.client_factory import get_discovery_client
from apps.tsps.models import TSP, TSPTypes
from apps.wizard.models import Wizard
from apps.discovery.serializers import ShareableDataAttributesInputSerializer

discovery_client = get_discovery_client()


@dataclass
class AdminInfo:
    email: str
    first_name: str
    last_name: str


class Command(BaseCommand):
    def handle(self, *args, **options):
        with open(
            "/src/apps/accounts/management/commands/generated_tsp_data.json"
        ) as file:
            list_of_tsps = json.load(file)

        admin_group: Group = Group.objects.get(name=GroupCodes.ADMIN)

        legal_representative_group: Group = Group.objects.get(
            name=GroupCodes.LEGAL_REPRESENTATIVE
        )
        import time
        start = time.time()
        count = 0
        for tsp_data in list_of_tsps:
            if TSP.objects.filter(name=tsp_data["TSP Name"]).exists():
                continue
            tsp_type = TSPTypes.objects.get(name=tsp_data["TSP Type"])
            tsp = TSP(
                name=tsp_data["TSP Name"],
                legal_name=tsp_data["Legal Name"],
                vat=tsp_data["Vat"],
                address=tsp_data["Address"],
                country=tsp_data["Country Code"],
                tsp_type=tsp_type,
            )
            tsp.save()
            discovery_client.create_tsp(
                tsp_id=str(tsp.id),
                name=tsp.name,
                tsp_type=tsp.tsp_type.name,
                countries=tsp_data["Countries"],
                time_slots=tsp_data["Time Slots"],
            )

            legal_representative_data = tsp_data["CEO"]

            UserFactory.create(
                email=legal_representative_data["Email"],
                first_name=legal_representative_data["First Name"],
                last_name=legal_representative_data["Last Name"],
                tsp=tsp,
                status=UserStatuses.ACTIVE,
                groups=(legal_representative_group,),
            )
            admin_list = []
            for admin_data in tsp_data["Admins"]:
                UserFactory.create(
                    email=admin_data["Email"],
                    first_name=admin_data["First Name"],
                    last_name=admin_data["Last Name"],
                    tsp=tsp,
                    status=UserStatuses.ACTIVE,
                    groups=(admin_group,),
                )
                admin_list.append(
                    AdminInfo(
                        email=admin_data["Email"],
                        first_name=admin_data["First Name"],
                        last_name=admin_data["Last Name"],
                    )
                )

            wizard = Wizard(
                tsp=tsp,
                current_step="SIGNATURES",
                status="COMPLETED",
            )
            wizard.save()
            new_data_attributes = {
                "accepted_attrs": tsp_data["Data Attributes"]
            }
            serializer = ShareableDataAttributesInputSerializer(
                data=new_data_attributes
            )
            serializer.is_valid(raise_exception=True)

            discovery_client.update_tsp_data_attributes(
                tsp_id=str(tsp.id),
                data_reqs_node_ids=serializer.validated_data["accepted_attrs"],
            )
            self.stdout.write(f"{tsp.name} was Created")
            count += 1
        end = time.time()
        self.stdout.write(f"{end - start} seconds")
        self.stdout.write(f"{count} tsps were created")
