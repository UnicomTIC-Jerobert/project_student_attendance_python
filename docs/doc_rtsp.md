**USER**
Im having 4 ip cameras fixed with dvr , brand is hikvision , how can i get the RTSP url , username and password

**RESPONSE**
To get the RTSP stream for your Hikvision DVR (or NVR), you need to construct a specific URL using your device's IP address, port, and your login credentials. 

Here is the step-by-step guide on how to find your Username, Password, and construct the RTSP URL.

### 1. The Hikvision RTSP URL Formula
For almost all Hikvision DVRs and NVRs, the standard RTSP URL looks like this:
`rtsp://[username]:[password]@[IP_address]:[port]/Streaming/Channels/[channel_number][stream_type]`

---

### 2. How to find your Username and Password
There is no "secret" or separate RTSP password. 
* **Username:** This is almost always **`admin`**.
* **Password:** This is the **exact same password** you use to log into the DVR system when you are looking at it on a monitor, or when using the iVMS-4200 app/Hik-Connect app. *(Note: Older Hikvision models used `12345` as a default, but newer models force you to create a secure password during initial setup).*

---

### 3. How to find your DVR's IP Address & Port
You need the local IP address of your DVR. Here are the easiest ways to find it:
* **Directly on the DVR:** Right-click the screen, go to **Menu > Configuration > Network > General**. Note the "IPv4 Address". 
* **Using a PC (Best Method):** Download the **Hikvision SADP Tool** on a computer connected to the same Wi-Fi/network as the DVR. It will scan your network and show you the exact IP address of your DVR.
* **The Port:** The default RTSP port for Hikvision is **`554`**. (You can verify this in the DVR by going to Configuration > Network > More Settings > Port).

---

### 4. How to set the Channel and Stream Type
The end of the URL requires a 3-digit number. 
* The first digit(s) is the **Camera Channel Number** (1, 2, 3, or 4).
* The last digit is the **Stream Type**:
  * `1` = Main Stream (High-definition, best quality)
  * `2` = Sub-stream (Standard definition, best for mobile/slow internet)

**Examples:**
* `101` = Camera 1, Main Stream
* `102` = Camera 1, Sub-stream
* `201` = Camera 2, Main Stream
* `401` = Camera 4, Main Stream

---

### 5. Putting it all together
Let's assume your username is `admin`, your password is `MyPassword123`, and your DVR's IP address is `192.168.1.100`.

**To view Camera 1 (High Quality):**
`rtsp://admin:MyPassword123@192.168.1.100:554/Streaming/Channels/101`

**To view Camera 2 (High Quality):**
`rtsp://admin:MyPassword123@192.168.1.100:554/Streaming/Channels/201`

**To view Camera 4 (Low Quality/Sub-stream):**
`rtsp://admin:MyPassword123@192.168.1.100:554/Streaming/Channels/402`

---

### How to Test Your URL
The best way to test if your URL works is by using **VLC Media Player** on your computer:
1. Open VLC Media Player.
2. Click **Media** > **Open Network Stream** (or press CTRL+N).
3. Paste your customized RTSP URL into the box.
4. Click **Play**. The camera feed should appear.

### Troubleshooting (If it doesn't work)
If VLC won't play the video, check these settings on your DVR:
1. **Disable Stream Encryption:** Log into the DVR, go to Configuration > Network > Advanced Settings > Platform Access, and **turn off "Stream Encryption"**.
2. **Enable ONVIF/CGI:** Go to Configuration > Network > Advanced Settings > Integration Protocol. Check the boxes to enable **ONVIF** and **CGI**, and create an ONVIF user (use the same admin/password). Save and restart the DVR.
