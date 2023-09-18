# Using YAPF with your editor

YAPF is supported by multiple editors via community extensions or plugins.

- [IntelliJ/PyCharm](#intellijpycharm)
- [IPython](#ipython)
- [VSCode](#vscode)

## IntelliJ/PyCharm

Use the `File Watchers` plugin to run YAPF against a file when you perform a save.

1.  Install the [File Watchers](https://www.jetbrains.com/help/idea/using-file-watchers.html) Plugin
1.  Add the following `.idea/watcherTasks.xml` to your project. If you already have this file just add the `TaskOptions` section from below. This example uses Windows and a virtual environment, modify the `program` option as appropriate.
    ```xml
    <?xml version="1.0" encoding="UTF-8"?>
    <project version="4">
        <component name="ProjectTasksOptions">
            <TaskOptions isEnabled="true">
                <option name="arguments" value="-i $FilePathRelativeToProjectRoot$" />
                <option name="checkSyntaxErrors" value="true" />
                <option name="description" />
                <option name="exitCodeBehavior" value="ERROR" />
                <option name="fileExtension" value="py" />
                <option name="immediateSync" value="true" />
                <option name="name" value="yapf" />
                <option name="output" value="" />
                <option name="outputFilters">
                    <array />
                </option>
                <option name="outputFromStdout" value="false" />
                <option name="program" value="$PROJECT_DIR$/.venv/Scripts/yapf.exe" />
                <option name="runOnExternalChanges" value="true" />
                <option name="scopeName" value="Project Files" />
                <option name="trackOnlyRoot" value="false" />
                <option name="workingDir" value="$Projectpath$" />
                <envs />
            </TaskOptions>
        </component>
    </project>
    ```

## IPython

IPython supports formatting lines automatically when you press the `<Enter>` button to submit the current code block.

Make sure that the YAPF module is available to the IPython runtime:

```shell
pip install ipython yapf
```

pipx example:

```shell
pipx install ipython
pipx inject ipython yapf
```

Add following to `~/.ipython/profile_default/ipython_config.py`:

```python
c.TerminalInteractiveShell.autoformatter = 'yapf'
```

## VSCode

VSCode has deprecated support for YAPF in its official Python extension [in favor of dedicated formatter extensions](https://github.com/microsoft/vscode-python/wiki/Migration-to-Python-Tools-Extensions).

1. Install EeyoreLee's [yapf](https://marketplace.visualstudio.com/items?itemName=eeyore.yapf) extension.
1. Install the yapf package from pip.
   ```
   pip install yapf
   ```
1. Add the following to VSCode's `settings.json`:
   ```jsonc
   "[python]": {
       "editor.formatOnSaveMode": "file",
       "editor.formatOnSave": true,
       "editor.defaultFormatter": "eeyore.yapf"  # choose this extension
   },
   ```
