# Using YAPF with your editor

YAPF is supported by multiple editors via community extensions or plugins.

* [IntelliJ/PyCharm](#intellijpycharm)
* [VSCode](#vscode)

## IntelliJ/PyCharm
Use the `File Watchers` plugin to run YAPF against a file when you perform a save.

1.  Install the File Watchers Plugin
1.  Add the following to `.idea/watcherTasks.xml`. If you already have this file just add the `TaskOptions` section from below. This example uses Windows and a virtual environemtn, modify the `program` option as appropriate
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

## VSCode

1. Install the [yapf](https://marketplace.visualstudio.com/items?itemName=eeyore.yapf) plugin.
1. Install the yapf package since this extension didn't include it.
1. Setup vscode settings by editting settings.json in User scope or Workspace scope in following: Example of settings
```jsonc
  "[python]": {
    "editor.formatOnSaveMode": "file",
    "editor.formatOnSave": true,
    "editor.defaultFormatter": "eeyore.yapf"  # choose this extension
  },
```
