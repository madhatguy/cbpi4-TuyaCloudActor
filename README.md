# cbpi4-TuyaCloudActor

CraftBeerPi4 actor plugin that controls **Tuya Cloud** devices (switches, valves, smart plugs, relays, …) from the CBPi UI.

## What it does

- Stores Tuya Cloud credentials in **CBPi global settings**
- Lets you **discover Tuya device IDs** from an actor action (copy/paste into configuration)
- Turns the selected device **ON/OFF** from the dashboard

## Install (development)

From your CBPi4 Python environment:

```bash
pipx runpip cbpi4 install -e ./cbpi4-TuyaCloudActor
cbpi add cbpi4-TuyaCloudActor
```

Restart CBPi afterwards.

## Tuya Cloud setup (Developer Platform)

You need a Tuya Cloud project and API credentials.

- **Create a Tuya IoT project**
  - Go to the Tuya Developer Platform and create a **Cloud** project.
  - Select the correct **data center/region** for your account (this determines the API endpoint).
- **Link your Tuya app account**
  - Link the app account that owns your devices (commonly Smart Life / Tuya Smart).
- **Get credentials**
  - Note down **Access ID (Client ID)** and **Access Secret (Client Secret)** from the project.
- **Find your endpoint**
  - Your endpoint depends on region, for example:
    - `https://openapi.tuyaus.com` (US)
    - `https://openapi.tuyaeu.com` (EU)
    - `https://openapi.tuyacn.com` (CN)

## CBPi configuration

### 1) Set global Tuya settings

In CBPi UI go to **Settings** and set:

- **Tuya Endpoint**: your regional endpoint (example: `https://openapi.tuyaeu.com`)
- **Tuya Access ID**
- **Tuya Access Secret**
- **Tuya Username**: the login for your app account (email or phone)
- **Tuya Password**
- **Tuya Country Code**: e.g. `1`, `44`, `49`, `972`
- **Tuya App Schema**: typically `smartlife` or `tuyaSmart` (depends on your app)

Restart CBPi after saving settings (recommended).

### 2) Add an Actor

Go to **Hardware → Actors → Add**:

- **Type**: `Tuya Cloud Actor`
- **Device ID**: use the action **List Tuya Devices** (see below), then copy the device `id` here
- **DP Code**: the datapoint code to switch (defaults to `switch`)
  - Common values: `switch`, `switch_1`, `switch_led`

Save.

### 3) Use it

Add the actor to your dashboard and toggle it ON/OFF.

## How to find your Device ID in CBPi

After creating the actor (you can temporarily leave `Device ID` empty):

- Open the actor menu (3 dots) and run **List Tuya Devices**
- Check the CBPi logs for a list like: `{"name": "...", "id": "..."}`
- Copy the `id` into the actor’s **Device ID** field and save

## Finding the right DP code

Tuya devices don’t all use the same switch code.

This plugin includes an actor action:
- **Show Tuya Device Functions**: queries Tuya for the selected device’s supported function codes.

Use the returned `code` for the ON/OFF datapoint as your **DP Code**.

## Troubleshooting

- **Empty device dropdown**
  - Verify global credentials in CBPi settings.
  - Verify the endpoint matches your Tuya project region.
  - Make sure your Tuya cloud project is linked to the correct app account.
- **403 / permission errors**
  - Your cloud project may be missing required API permissions.
  - Ensure the project has device-control permissions enabled.
- **Switch doesn’t toggle**
  - Your device likely uses a different DP code (try `switch_1` / `switch_led`).

## Notes / limitations

- This plugin currently targets **simple on/off** control of a single datapoint (DP code).
- Dimming/PWM and multi-channel devices can be added later by exposing multiple DP codes and/or power control.

