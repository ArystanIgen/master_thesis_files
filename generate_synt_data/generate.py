import json
import random
import factory
from faker.providers import BaseProvider
from faker import Faker as OriginalFaker

# Load the data requirements
with open('data_requirements.json', 'r') as file:
    data_requirements = json.load(file)

# Mapping of TSP types to their data code prefixes
code_prefix_mapping = {
    "Airline": "AL",
    "Regional rail": "RRW",
    "Long distance rail": "LDRW",
    "Bus operators": "BUS",
    "DRT": "DRT",
    "Airport": "AP"
}

# Country to code mapping (ISO-like codes)
country_code_mapping = {
    "Germany": "DE",
    "France": "FR",
    "Italy": "IT",
    "Spain": "ES",
    "Netherlands": "NL",
    "Belgium": "BE",
    "Poland": "PL",
    "Czech Republic": "CZ",
    "Portugal": "PT",
    "Austria": "AT"
}


# Custom Provider for Faker
class TransportNameProvider(BaseProvider):
    def transport_company(self, type_code, country, company_name: str):
        types = {
            "Airline": ["Airlines", "Airways"],
            "Regional rail": ["Railroad", "Transit"],
            "Long distance rail": ["Railroad", "Lines"],
            "Bus operators": ["Lines", "Transit"],
            "DRT": ["Services", "Solutions"],
            "Airport": ["International Airport", "Airfield"]
        }
        descriptor = random.choice(["Connect", "Express", "Lines", "Network", "Swift", "Reliable", "Sol"])
        return f"{random.choice(types[type_code])} {company_name} {descriptor}"


faker = OriginalFaker()
faker.add_provider(TransportNameProvider)


class TransportServiceProviderFactory(factory.Factory):
    class Meta:
        model = dict

    tsp_type = factory.Iterator(["Airline", "Regional rail", "Long distance rail", "Bus operators", "DRT", "Airport"])
    countries = factory.LazyAttribute(lambda o: random.sample(
        ["Germany", "France", "Italy", "Spain", "Netherlands", "Belgium", "Poland", "Czech Republic", "Portugal",
         "Austria"],
        random.randint(1, 3) if o.tsp_type not in ["Airline", "Airport", "Long distance rail"] else random.randint(2, 5)
    ))
    # Choose a main country from the assigned countries (first one in the list)
    main_country = factory.LazyAttribute(lambda o: o.countries[0])
    name = factory.LazyAttribute(lambda o: faker.transport_company(o.tsp_type, o.main_country, faker.company()))
    provided_data = factory.LazyAttribute(lambda o: [
                                                        entry["code"] for entry in data_requirements
                                                        if entry["code"].startswith(code_prefix_mapping[o.tsp_type])
                                                    ][:random.randint(5, 10)])
    time_slots = factory.LazyAttribute(lambda _: random.sample(
        ["Mornings", "Afternoons", "Nights"], random.randint(1, 3)
    ))

    # Additional fields: legal_name, address, vat
    legal_name = factory.LazyAttribute(lambda o: f"{o.name} S.A.")
    address = factory.LazyAttribute(lambda o: f"{faker.street_address()}, {faker.city()}, {o.main_country}")
    vat = factory.LazyAttribute(lambda o: f"{o.main_country[:2].upper()}{random.randint(10000000, 99999999)}A")

    # CEO information
    CEO = factory.LazyAttribute(lambda o: {
        "Email": f"{faker.first_name().lower()}.{faker.last_name().lower()}@{o.name.replace(' ', '').lower()}.{country_code_mapping.get(o.main_country, 'xx').lower()}",
        "First Name": faker.first_name(),
        "Last Name": faker.last_name()
    })

    # Admins information
    Admins = factory.LazyAttribute(lambda o: [
        {
            "Email": f"{faker.first_name().lower()}.{faker.last_name().lower()}@{o.name.replace(' ', '').lower()}.{country_code_mapping.get(o.main_country, 'xx').lower()}",
            "First Name": faker.first_name(),
            "Last Name": faker.last_name()
        },
        {
            "Email": f"{faker.first_name().lower()}.{faker.last_name().lower()}@{o.name.replace(' ', '').lower()}.{country_code_mapping.get(o.main_country, 'xx').lower()}",
            "First Name": faker.first_name(),
            "Last Name": faker.last_name()
        }
    ])


def generate_tsp_data(num_entries):
    data_list = []
    for _ in range(num_entries):
        tsp_info = TransportServiceProviderFactory.build()
        main_country_code = country_code_mapping.get(tsp_info['main_country'], "XX")

        # Construct the final object
        tsp_object = {
            "TSP Name": tsp_info['name'],
            "Legal Name": tsp_info['legal_name'],
            "Address": tsp_info['address'],
            "Vat": tsp_info['vat'],
            "Countries": [tsp_info['main_country']],
            "Country Code": main_country_code,
            "TSP Type": tsp_info['tsp_type'],
            "Data Attributes": tsp_info['provided_data'],
            "Time Slots": tsp_info['time_slots'],
            "CEO": tsp_info['CEO'],
            "Admins": tsp_info['Admins']
        }

        data_list.append(tsp_object)
    return data_list


# Number of entries to generate
num_entries = 10  # You can change this to generate more or fewer entries

# Generate data
generated_tsp_data = generate_tsp_data(num_entries)

# Output the generated data to a JSON file
with open('generated_tsp_data.json', 'w') as file:
    json.dump(generated_tsp_data, file, indent=4)

print("Generated JSON file with TSP data, including Country Code, CEO, and Admins.")
