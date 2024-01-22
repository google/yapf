A fork of python's lib2to3 with select features backported from black's blib2to3.

Reasons for forking:

- black's fork of lib2to3 already considers newer features like Structured Pattern matching
- lib2to3 itself is deprecated and no longer getting support

Maintenance moving forward:
- Most changes moving forward should only have to be done to the grammar files in this project.
