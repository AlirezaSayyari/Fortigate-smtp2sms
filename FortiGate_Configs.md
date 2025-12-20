## 🔧 FortiGate Configuration (With VDOM Support)

FortiGate must send OTP emails to the Docker SMTP Gateway.
If your firewall is using **VDOMs**, email configuration must be applied **inside the correct VDOM** (usually the VDOM handling VPN traffic, commonly `root` or `FG-traffic`).

### 1️⃣ Enter VDOM Context

Replace `<YOUR_VDOM>` with the VDOM where VPN users exist.

```bash
config vdom
edit <YOUR_VDOM>
```

Example:

```bash
config vdom
edit root
```

---

### 2️⃣ Configure SMTP Server (Your Docker Gateway)

Set:

* `server` = IP of your Docker SMTP Gateway
* `source-ip` = FortiGate interface IP in same network
* Authentication disabled

```bash
config global
config system email-server
    set server "192.168.X.X"
    set port 25
    set source-ip 192.168.X.Y
    set authenticate disable
end

config system sms-server
    edit "FGSms"
    set mail-server "sms.company.com"
end
```

Notes:

* Port must be **25**
* No TLS
* No username / password
* Source IP should be reachable from Docker host
* Same IP must be allowed in gateway config as trusted source

Exit VDOM when done:

```bash
end
```

---

### 3️⃣ Assign “sms” as OTP Delivery Method for VPN Users

Users must have sms OTP enabled.

#### System Users

```bash
config user local
edit <USERNAME>
    set two-factor sms
    set email-to "user@company.com"
    set sms-server custom
    set sms-custom-server "FGSms"
    set sms-phone "09123456789"
next
end
```

---

### 4️⃣ Assign a physical port in mgmt vdom to same vlan with SMTP Server (Your Docker Gateway) and connect it to core switch with access to SMTP Server vlan

config vdom
edit Mgmt
config system interface
edit "port1"
  set vdom "Mgmt"
        set ip 192.168.X.Y 255.255.255.Z
        set allowaccess ping
        set type physical
        set role lan
        set snmp-index 2
    next
end

---

### 5️⃣ (Optional) Test SMS Delivery from FortiGate

Run inside same VDOM:

```bash
execute test sms-server
```

If successful, Docker logs should show SMTP communication.

---

### 6️⃣ Make Sure Routing Exists to Docker Host

If Docker server is in another subnet, ensure routing exists in the same VDOM:

```bash
config router static
edit 0
    set dst 192.168.X.X 255.255.255.255
    set gateway <NEXT_HOP>
    set device <INTERFACE>
next
end
```

---

### 7️⃣ Firewall Policy Allow SMTP Outbound (If Restricted)

If outbound filtering exists, allow FortiGate to send to gateway:

```bash
config firewall policy
edit 0
    set name "SMTP_to_SMS_Gateway"
    set srcintf "<VDOM_INTERFACE>"
    set dstintf "<INTERFACE_TO_GATEWAY>"
    set srcaddr "all"
    set dstaddr "SMS-Gateway"
    set action accept
    set service "SMTP"
    set schedule "always"
next
end
```

---

### ✅ Final Checklist

| Requirement                              | Status |
| ---------------------------------------- | ------ |
| VDOM Correctly Selected                  | ✔      |
| SMTP Configured                          | ✔      |
| Auth Disabled                            | ✔      |
| VPN Users Email Format `<MOBILE>@domain` | ✔      |
| Routing to Docker Host                   | ✔      |
| Firewall Allow SMTP                      | ✔      |