-- With LUA > 5.3 to use the table.move

--local inspect = require('inspect')

-- Define a wait/sleep function since Lua does not have one (Linux only)
function wait(seconds)
   local start = os.time()
   repeat until os.time() > start + seconds
 end

-- From https://stackoverflow.com/a/27028488/7189378
function dump(o)
    if type(o) == 'table' then
       local s = '{ '
       for k,v in pairs(o) do
          if type(k) ~= 'number' then k = '"'..k..'"' end
          s = s .. '['..k..'] = ' .. dump(v) .. ','
       end
       return s .. '} '
    else
       return tostring(o)
    end
 end

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
 
 function equally_assign(assignments)
   local x = 1
   local temp = { [1] = {}, [2]= {} }
   local step = #assignments[1]/2
   print(step)
   if #assignments[1] == 2 then
    temp[1] = dump{unpack(assignments[1], x, x)}
    temp[2] = dump{unpack(assignments[1], x+1, x+1)}
   else
     for i = 1, #assignments[1] do
       temp[i] = dump{unpack(assignments[1], x, x + step-1)}
       x = x + step -1
       print("Progress..")
       print(dump(temp))
     end
  end
  print("Final..")
  print(dump(temp))
   --print(dump(assignments))
 end
 
 local servers = {1, 2, 3, 4}
--  local users = {1, 2, 3, 4, 5, 6}
 local users = {}
 
 -- Initial assignments
 local assignments = {
   -- [1] = {users[1], users[2], users[3], users[4]},
   -- [1] = {users[1], users[2], users[3], users[4], users[5]},
     --[1] = {users[1], users[2], users[3]},
     --[1] = {users[1], users[2]},
     [1] = {},
     [2] = {}
   -- ["172.20.0.3:80"] = {},
   -- ["172.20.0.4:80"] = {},
 }
 
 --print(dump(assignments))
 
 -- someList = { 'a', 'b', 'c' , 'd' }
 -- subList = { unpack( someList, 1, 2 ) }
 -- print( unpack(subList) )
 
 -- subList = { unpack( someList, 3, 4 ) }
 -- print( unpack(subList) )
 
 -- print(#assignments)
 --equally_assign(assignments)

-- print(_VERSION)
 
-- local new_user = 1
local new_user = "192.168.1.2"
local inc_user = 2
local splits = 2
-- while true do
for i=1,6 do
   
   -- table.insert(users, new_user)
   -- users[new_user] = new_user
   users[inc_user] = new_user
   -- if #users > 6 then
   --    splits = 3
   -- end

   old_key = nil
   for i, chunk in splitByChunk(users, splits) do
      -- print(dump(chunk))
      
      if i > splits then
         --  table.insert(assignments[i-splits], dump(chunk))
         for k, v in pairs(chunk) do
            table.insert(assignments[i-splits], v)
         end
      else
         assignments[i] = chunk;
      end
      
      

      -- local key, value = next(assignments, old_key)
      -- if key == nil then
      --    key, value = next(assignments, key)
      -- end
      -- assignments[key] = chunk;
      -- old_key = key

      
   end

   -- TODO: This needs to be done dynamically somehow
   assignments["172.20.0.3:80"] = assignments[1];
   assignments["172.20.0.4:80"] = assignments[2];
   table.remove(assignments, 1);
   table.remove(assignments, 1);

   print("Final assignments");
   print(dump(assignments));
   print("=======");
   -- wait(2);

   -- Simulate the increase of users (it can be anything)
   inc_user = inc_user + 1;
   new_user = new_user:sub(1, -2);
   new_user = new_user .. inc_user;

   
end