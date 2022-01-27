### Pre-req on Mac
xcode-select --install

### Everyone has HomeBrew installed, just iinstall pyenv


brew install pyenv

### Once the install is finished, you have one further step to complete to ensure pyenv can be added to your PATH, allow it to work correctly on the command line, and to enable shims and autocompletions.

echo 'export PYENV_ROOT="$HOME/.pyenv"' >> ~/.zshrc\necho 'export PATH="$PYENV_ROOT/bin:$PATH"' >> ~/.zshrc\necho -e 'if command -v pyenv 1>/dev/null 2>&1; then\n  eval "$(pyenv init -)"\nfi' >> ~/.zshrc
  
### To see a list of all the available versions of Python that you can install through pyenv simply type the following into the Terminal.
pyenv install --list

### Once you have identified the version you want, enter the following command to install it 
pyenv install 3.7.12


### Entering the command pyenv versions will show you all versions of Python you currently have installed on your computer. To set a particular version to be your default global version, simply enter the following command (replace 3.9.1 with your chosen version). pyenv global x.x.x

### You can also set a specific Python version to be used in a particular directory by navigating into that directory and then running the following command

cd <working directory>
pyenv local 3.7.12

  ### Firstly, you will need to install pyenv-virtualenv. You can do this by entering the following command into the Terminal.
brew install pyenv-virtualenv

### Using the Terminal, navigate into the directory in which you are going to create the virtual environment

cd <working_directory>

 ### The version number aligns to the Python version you just set as the local version for the environment, and the final section is the name of the virtual environment. My personal preference is to prefix the name with ‘venv’, and then align the name of the virtual environment to the name of the directory it relates to.

 pyenv virtualenv 3.7.12 venv_sko23_keynote

 ### The final step is to set the local python version for the directory as the virtual environment.
 pyenv local venv_sko23_keynote

 ### Activating and de-activating the environment is achieved with the following commands.
 pyenv activate venv_sko23_keynote
 pyenv deactivate


 ### To enable auto-activation and de-activation of the virtual environment as you navigate in and out of the associated directory, simply enter the following command in the Terminal to update the .zshrc file with the required information.
 echo 'eval "$(pyenv virtualenv-init -)"' >> ~/.zshrc