# PROTECT-5 — nginx + Matrix security review (read-only)

**Linear:** BEL-55  
**Date:** 2026-08-04  
**Mode:** documentation + observation only (no live config change)

## Listening snapshot
```
LISTEN 0      200                                      127.0.0.1:54329      0.0.0.0:*    users:(("postgres",pid=380495,fd=8))       
LISTEN 0      4096                                     127.0.0.1:50080      0.0.0.0:*                                               
LISTEN 0      511                                        0.0.0.0:3100       0.0.0.0:*    users:(("node",pid=380474,fd=40))          
LISTEN 0      511                                        0.0.0.0:443        0.0.0.0:*                                               
LISTEN 0      511                                        0.0.0.0:80         0.0.0.0:*                                               
LISTEN 0      4096                                     127.0.0.1:11434      0.0.0.0:*                                               
LISTEN 0      10                                       127.0.0.1:44800      0.0.0.0:*    users:(("rygel",pid=4146776,fd=15))        
LISTEN 0      511                                           [::]:443           [::]:*                                               
LISTEN 0      511                                           [::]:80            [::]:*                                               
LISTEN 0      10         [fe80::6c2b:85ff:fe04:78d0]%vethdccf177:55555         [::]:*    users:(("rygel",pid=4146776,fd=59))        
LISTEN 0      10         [fe80::ec85:8eff:fe4d:208a]%veth8cfc05e:45177         [::]:*    users:(("rygel",pid=4146776,fd=55))        
LISTEN 0      10             [fe80::e0cc:d978:e05f:2013]%enp10s2:59383         [::]:*    users:(("rygel",pid=4146776,fd=39))        
LISTEN 0      10     [fe80::d071:b1ff:feba:d67d]%br-44a69c93fc4b:45166         [::]:*    users:(("rygel",pid=4146776,fd=51))        
LISTEN 0      10             [fe80::f878:f1ff:fe6c:abe5]%docker0:55483         [::]:*    users:(("rygel",pid=4146776,fd=47))        
LISTEN 0      10             [fe80::3617:ebff:fee0:b11f]%enp0s25:48648         [::]:*    users:(("rygel",pid=4146776,fd=43))        

```

## Findings / recommendations
1. Paperclip :3100 must remain private/tailnet — not public WAN
2. Agent Zero :50080 localhost-only preferred
3. Matrix stack: confirm no open registration; TLS on edge if exposed
4. Prefer reverse proxy with auth for any public path
5. Follow-up: human applies nginx/Caddy hardening when ready

## Status
Review artifact filed. Live hardening remains Todo until operator applies changes.
