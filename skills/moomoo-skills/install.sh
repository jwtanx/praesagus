# Curl the zip file here
curl -L -o moomoo.zip https://www.moomoo.com/skills/moomoo.zip

# Unzip the file
unzip moomoo.zip

# Move all the folder from the moomoo folder to current directory
mv moomoo/* .

# Remove the zip file
rm moomoo.zip
rm -rf moomoo