local balancer = require("ngx.balancer")
local server = "172.20.0.3:80"

if ngx.var.remote_addr == "172.20.0.6"  then
    server = "172.20.0.3:80"
end

if ngx.var.remote_addr == "172.20.0.5"  then
    server = "172.20.0.3:80"
end

ok, err = balancer.set_current_peer(server)
if not ok then
    ngx.log(ngx.ERR, "set_current_peer failed: ", err)
    return ngx.exit(500)
end