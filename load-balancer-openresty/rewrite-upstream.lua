
--set $upstream "backend"

ngx.req.read_body()

local data = ngx.req.get_body_data()
if ngx.var.remote_addr == "172.20.0.5"  then
    -- ngx.var.upstream = "backend"
    ngx.var.upstream = "backend2"
end