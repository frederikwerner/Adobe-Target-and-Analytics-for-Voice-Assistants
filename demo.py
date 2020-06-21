
#We are going to use requests to call the APIs
import requests

#Placeholder, adapt to the IDs available on your Assistant
alexa_userID = "abc123"
alexa_deviceID = "def456"
custom_userID = "ghi789"

#Config for Adobe Tools. Change as needed. ECID should be persisted by your Skill.
adobe_orgid = "9B24H87FJ8180A4C98A2@AdobeOrg"
adobe_ecid = ""
adobe_targetproperty = "f3we51a0-63be-i7gb-e23e-b738n2854c9de"
adobe_targetdomain = "probablyyourcompanyname"
adobe_targetcode = "alsoyourcompanybutshorter"
adobe_targetsession = "Session ID from assistant, user ID if not available"
adobe_rsid = "Analytics Report Suite ID"
adobe_analyticstrackingserver = "company.sc.omtrdc.net"

#Function to call the ECID service with or without an ECID. Returns response as object from JSON
def get_visitor_object(ecid=""):
  if ecid:
    r = requests.get('https://dpm.demdex.net/id?d_mid='+ecid+'d_orgid='+adobe_orgid+'&d_ver=2&d_cid=alexaUserID%01'+alexa_userID+'%010&d_cid=alexaDeviceID%01'+alexa_deviceID+'%010')
  else:
    r = requests.get('https://dpm.demdex.net/id?d_orgid='+adobe_orgid+'&d_ver=2&d_cid=alexaUserID%01'+alexa_userID+'%010&d_cid=alexaDeviceID%01'+alexa_deviceID+'%010')
  print("Retrieved Visitor Object from ", r.url)
  visitor_object = r.json()
  return visitor_object

#Function to sync IDs with the ECID Service
def sync_ids(ecid,ids):
  idstring = ""
  for name, value, authstatus in ids:
    idstring = idstring + "&d_cid=" + name + "%01" + value + "%01" + authstatus
  r = requests.get('https://dpm.demdex.net/id?d_mid='+ecid+'&d_orgid='+adobe_orgid+'&d_ver=2'+idstring)
  print("Synced IDs to ", r.url)

#Function to call Adobe Target with information about the current state of the app
def get_mbox_content(mbox,intent,slots=[],profile_params=[],capabilities=[],ids=[]):
  #Construct request
  target_payload = {
    'context':{
      "channel":"web"
    },
    "id":{
      "marketingCloudVisitorId": adobe_ecid
    },
    "property" : {
      "token": adobe_targetproperty
    },
    "experienceCloud": {
      "analytics": {
        "logging": "client_side"
      },
      "audienceManager": {
        "locationHint": str(visitor_object["dcs_region"]),
        "blob": visitor_object["d_blob"]
      }
    },
    "execute": {
      "mboxes" : [
        {
          "name" : mbox,
          "index" : 1,
          "parameters":{
            "intent":intent
          }
        }
      ]
    }
  }
  #Iterate Intent Slots and add as mBox parameters
  for slot,content in slots:
    target_payload["execute"]["mboxes"][0]["parameters"]["slot_"+slot] = content

  #Iterate device capabilities and add them as mBox parameters
  for capability in capabilities:
    target_payload["execute"]["mboxes"][0]["parameters"]["capabilities_"+capability] = "true"

  #Add profile parameters
  if len(profile_params)>0:
    target_payload["execute"]["mboxes"][0]["profileParameters"]={}
    for param,content in profile_params:
      target_payload["execute"]["mboxes"][0]["profileParameters"][param] = content

  #Add IDs to sync with Target
  if len(ids) > 0:
    target_payload["id"]["customerIds"] = []
    for id,content in ids:
      target_payload["id"]["customerIds"].append({"id":content,"integrationCode":id,"authenticatedState":"authenticated"})

  #Request the mBox content from Target
  r = requests.post('https://'+adobe_targetdomain+'.tt.omtrdc.net/rest/v1/delivery?client='+adobe_targetcode+'&sessionId='+adobe_targetsession, json = target_payload)
  target_object = r.json()
  print("Requested Target Mbox from ",r.url)

  #Send information about Target Activity to Analytics (for Target, A4T)
  r = requests.get("https://"+adobe_analyticstrackingserver+"/b/ss/"+adobe_rsid+"/0/1?c.a.AppID=Spoofify2.0&c.OSType=Alexa&mid="+visitor_object["d_mid"]+"&pe="+target_object["execute"]["mboxes"][0]["analytics"]["payload"]["pe"]+"&tnta="+target_object["execute"]["mboxes"][0]["analytics"]["payload"]["tnta"])
  print("Tracked A4T to ", r.url)

  #Return the mBox content
  if "options" in target_object["execute"]["mboxes"][0]:
    return target_object["execute"]["mboxes"][0]["options"][0]["content"]
  else:
    return ""

#Function to track the current Intent to Analytics
def track_intent(intent,slots=[],capabilities=[],install=False,launch=False):
  #Setup base url
  analytics_url = "https://"+adobe_analyticstrackingserver+"/b/ss/"+adobe_rsid+"/0/1?"
  #If the Skill was just installed, track that information
  if install:
    analytics_url += "c.a.InstallEvent=1&c.a.InstallDate=[currentDate]&"
    
  #If this is the start of a new session, set this flag to track a launch event
  if launch:
    analytics_url += "c.a.LaunchEvent=1&"

  #Iterate over Slots and put them in List var 1 (l1) as "key=value" to allow auto-classification
  if len(slots)>0:
    slotlist = []
    for slot,content in slots:
      slotlist.append(slot+"="+content)
    slotstring = ",".join(slotlist)
    analytics_url += "l1="+slotstring+"&"

  #Add device capabilities to List var 2 (l2)
  if len(capabilities)>0:
    capabilitiesstring = ",".join(capabilities)
    analytics_url += "l2="+capabilitiesstring+"&"

  #Add other Analytics variables
  analytics_url += "c.a.AppID=Spoofify2.0&c.OSType=Alexa&c.Intent="+intent+"&mid="+visitor_object["d_mid"]+"&pageName="+intent+"&aamlh="+str(visitor_object["dcs_region"])+"&aamb="+visitor_object["d_blob"]

  #Sent off Analytics requests
  r = requests.get(analytics_url)
  print("Tracked Intent to ",r.url)

#Information about current Intent, it's Slots and device capabilities
intent = "Launch Intent"
slots = [("username","Gerald"),("slot2","value2")]
capabilities = ["Capa 1","Capa 2","Capa 3","Capa 4"]

#Receive ECID information and store it
visitor_object = get_visitor_object(adobe_ecid)
adobe_ecid=visitor_object["d_mid"]

#Sync IDs to ECID
sync_ids(adobe_ecid,[("userid","1234","1")])

#Query Target and track to Analytics
target_response = get_mbox_content("Voice Response", intent, slots,[("param1","value1"),("param2","value2")],capabilities,[("userid","1234"),("id2","2345")])
track_intent(intent, slots, capabilities)

print(target_response)
