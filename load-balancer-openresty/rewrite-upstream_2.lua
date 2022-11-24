local balancer = require("ngx.balancer")
local server = "172.20.0.3:80"

if ngx.var.remote_addr == "172.20.0.6"  then
    -- server = "172.20.0.4:80"
    -- ngx.shared.request_counters:set("First", 1)
    if ngx.shared.request_counters:get("First") == 1 then
        server = "172.20.0.4:80"
       ngx.shared.request_counters:set("First", 2)
    --end
    elseif ngx.shared.request_counters:get("First") == 2 then
        server = "172.20.0.3:80"
        ngx.shared.request_counters:set("First", 1)
    end
end

if ngx.var.remote_addr == "172.20.0.5"  then
    server = "172.20.0.3:80"
end

ok, err = balancer.set_current_peer(server)
if not ok then
    ngx.log(ngx.ERR, "set_current_peer failed: ", err)
    return ngx.exit(500)
end