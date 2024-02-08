# X-ray Podcasts App: Starter app

This is *the* demo app for the Build Audio AI Apps with Python and AssemblyAI course.

## Running the app

#1. **Create and activate a virtual environment** in this folder, call it `venv` 
(the prompt command names it the same as this folder for display):

```shell
python -m venv venv --prompt .
. venv/bin/activate       # <-- macOS and Linux
venv/scripts/activate.bat # <-- Windows
pip install --upgrade pip # Why is it always out of date?
```

#2. **Install the required dependencies** (e.g. FastAPI) with the virtual environment activated:

```shell
pip install -r requirements.txt
```

#3. Open the folder containing the README.md file in **your editor**.

#4. Get the **latest Docker container** for MongoDB (with Docker Desktop or OrbStack running).

```shell
docker pull mongo
```
#5. Create a **persistent storage that MongoDB can use** inside of Docker so that your data doesn't vanish each restart.

```shell
docker volume create mongodata
```

#6. **Launch the Docker container** to run MongoDB in the background. This will run MongoDB available to all apps on your machine (but not outside of it - hence the 127.0.0.1 in the command). It will continue to run it until you stop it via `docker stop mongosvr` or you stop Docker Desktop or you log off your computer.

```shell
docker run -d --rm -p 127.0.0.1:27017:27017 -v mongodata:/data/db --name mongosvr mongo
```

If you're new to Docker, here is what this somewhat obtuse command means. Don't worry, you won't need to decipher it. Just run it before you try to launch the app in your editor.

* `-d` means daemon mode, run unattended in the background as a service
* `--rm` delete all data and evidence of the MongoDB container (not image) on stop. This does not include the separate data volume named `mongodata` you created in step 5.
* `-p` Listen on localhost port 27017 and map all traffic into the container to its internal port 27017 (i.e. the mongod server)
* `-v` Use the persistent volume named `mongodata` for all files and storage under the `/data/db` folder (MongoDB's database files).
* `--name` Set a fixed name for the container rather than an auto generated on like `focal_cats`. This makes it easier to issue commands to it later if needed (such as stop).
* `mongo` (at the end) is the name of the image to base the running container off. This comes from our *docker pull **mongo*** command in step 4.
