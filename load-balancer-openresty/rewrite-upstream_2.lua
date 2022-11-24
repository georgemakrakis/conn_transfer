local balancer = require("ngx.balancer")
local server = "172.20.0.3:80"


local function splitByChunk(assignments, chunkSize)
    -- our current index
   local i = 1
   -- our chunk counter
   local count = 0
   return function()
     -- abort if we reached the end of lst
     if i > #assignments then return end
     -- get a slice of lst
     local chunk = table.move(assignments, i, i + chunkSize -1, 1, {})
     -- next starting index
     i = i + chunkSize
     count = count + 1
     return count, chunk
   end
end

local server_assignments = {
    ["172.20.0.3:80"] = {},
    ["172.20.0.4:80"] = {},
}

-- local clients = {}
-- Check if the client already exists and if so evict it and assign again
-- table.insert(clients, new_client)

clients[ngx.var.remote_addr] = ngx.var.remote_addr

local splits = 2
for i, chunk in splitByChunk(clients, splits) do
    if i == 1 then
        local key, value = next(a, nil)
        server_assignments[key] = chunk;
    elseif i > 1 then
        local key, value = next(a, i-1)
        server_assignments[key] = chunk;
    end
end

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