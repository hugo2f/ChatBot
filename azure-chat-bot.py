# import libraries
import os
from azure.core.credentials import AzureKeyCredential
from azure.ai.language.conversations import ConversationAnalysisClient
from azure.identity import DefaultAzureCredential
from azure.mgmt.resource import ResourceManagementClient
from azure.mgmt.web import WebSiteManagementClient
from azure.mgmt.consumption import ConsumptionManagementClient

# resource types
resource_type = {
    "virtual machines": "Microsoft.Compute/virtualMachines",
    "storage accounts": "Microsoft.Storage/storageAccounts",
    "web apps": "Microsoft.Web/sites",
    "webapps": "Microsoft.Web/sites",
    "app services": "Microsoft.Web/sites",
    "virtual networks": "Microsoft.Network/virtualNetworks",
    "load balancers": "Microsoft.Network/loadBalancers",
    "key vaults": "Microsoft.KeyVault/vaults",
    "event hubs": "Microsoft.EventHub/namespaces",
    "function apps": "Microsoft.Web/sites/functions",
    "container registries": "Microsoft.ContainerRegistry/registries",
    "bot services": "Microsoft.BotService/botServices",
    "language services": "Microsoft.CognitiveServices/accounts",
    "search services": "Microsoft.Search/searchServices",
}

# account credentials
subscription_id = os.environ["AZURE_SUBSCRIPTION_ID"]
credential = DefaultAzureCredential()
resource_client = ResourceManagementClient(credential, subscription_id)
web_client = WebSiteManagementClient(credential, subscription_id)
consumption_client = ConsumptionManagementClient(credential, subscription_id)

# account information
resource_groups = list(resource_client.resource_groups.list())
resources = list(resource_client.resources.list())
web_apps = web_client.web_apps.list()

# get secrets
clu_endpoint = os.environ["AZURE_CONVERSATIONS_ENDPOINT"]
clu_key = os.environ["AZURE_CONVERSATIONS_KEY"]
project_name = os.environ["AZURE_CONVERSATIONS_PROJECT_NAME"]
deployment_name = os.environ["AZURE_CONVERSATIONS_DEPLOYMENT_NAME"]

# analyze query
client = ConversationAnalysisClient(clu_endpoint, AzureKeyCredential(clu_key))


def list_resource_of_type(_type):
    return [r for r in resources if r.type == _type]


def print_resources(resource_list):
    for r in resource_list:
        print(f"Name: {r.name}, Type: {r.type}, Location: {r.location}\n")


def get_resource_status(resource):
    id = resource.id.split('/')
    index = id.index("resourceGroups")
    rg = id[index + 1]

    if resource.type == "Microsoft.Web/sites":
        web_app = web_client.web_apps.get(rg, resource.name)
        return f"Status: {web_app.state}"


def process_query(query):
    result = client.analyze_conversation(
        task={
            "kind": "Conversation",
            "analysisInput": {
                    "conversationItem": {
                        "participantId": "1",
                        "id": "1",
                        "modality": "text",
                        "language": "en",
                        "text": query
                    },
                "isLoggingEnabled": False
            },
            "parameters": {
                "projectName": project_name,
                "deploymentName": deployment_name,
                "verbose": True
            }
        }
    )

    # result summary
    print(result)
    intent = result['result']['prediction']['topIntent']
    entities = result['result']['prediction']['entities']
    _type = target = ""
    if entities:
        if intent == "ListResources" or intent == "CountResources":
            _type = entities[0]['text'].lower()
            # print(f"text: {_type}")
        elif intent == "CheckStatus":
            try:
                _type = next((entity for entity in entities if entity['category'] == 'type'))[
                    'text'].lower()
                if _type[-1] != 's':
                    _type += 's'
            except StopIteration:
                pass

            try:
                target = next((entity for entity in entities if entity['category'] == 'target'))[
                    'text'].lower()
                # print(f'text: {target}')
            except StopIteration:
                pass
    else:
        intent = ""
    print('----------')

    # process query
    if intent == 'ListResources':
        print('ListResources', _type)
        if _type == 'resource groups':
            for rg in resource_groups:
                print(f"Name: {rg.name}, Location: {rg.location}")
        elif _type == "resources":
            print_resources(resources)
        elif _type in resource_type:
            print_resources(list_resource_of_type(resource_type[_type]))
        else:
            print("Sorry, I don't understand the request")
    elif intent == "CountResources":
        print('CountResources', _type)
        if _type == "resource groups":
            print(f"You have {len(resource_groups)} resource groups")
        elif _type == "resources":
            print(f"You have {len(resources)} resources")
        elif _type in resource_type:
            print(len(
                f"You have {list_resource_of_type(resource_type[_type])} resources"))
        else:
            print("Sorry, I don't understand the request")
    elif intent == "CheckStatus":
        print('CheckStatus', _type, target)
        if target == "bill":
            
            return
        if _type:
            resource = next((r for r in resources if r.name ==
                            target and r.type == resource_type[_type]), None)
        else:
            resource = next((r for r in resources if r.name == target), None)
        if resource:
            print(get_resource_status(resource))
        else:
            print("Resource not found")
    else:
        print("Sorry, I don't understand the request")
    print()


with client:
    while True:
        query = input("> ")
        if query == "quit":
            break
        process_query(query)
