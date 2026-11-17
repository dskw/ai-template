# Dependencies

The structural dependencies of the project. A step names each row whose trigger it meets.

## Dependencies
| ID | Trigger | Action | Validation |
|---|---|---|---|
| DEP-01 | A step adds one more instance of a type that the project already has, such as a data file, a message or a handler. | Add only the own places of the instance. When it repeats knowledge of the type in another place, stop and record a structural extension. | The reviewer names each place outside the instance that repeats knowledge of the type as Shotgun Surgery, or states that there is none. |

## Records
- added DEP-01 template 2026-11-16
- changed DEP-01 A53 2026-11-17
