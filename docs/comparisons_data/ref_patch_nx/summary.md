# Reflectivity patching survey

| method | joins | median err | median χ²/dof | flagged |
|---|---|---|---|---|
| legacy | 3 | 0.00457 |  | 0 |
| interp | 3 | 0.00461 | 1.16 | 0 |
| interp_log | 3 | 0.00461 | 1.15 | 0 |
| coincident | 3 | 0.00715 | 1.73 | 0 |
| joint_o2_e0 | 3 | 0.00466 | 1.14 | 3 |
| joint_o4_e2 | 3 | 0.00426 | 0.83 | 3 |
| joint_o4_e4 | 3 | 0.00426 | 0.71 | 3 |
| joint_o4_e4_raw | 3 | 0.00426 | 0.71 | 3 |
| joint_o4_e4_log | 3 | 0.00426 | 0.71 | 3 |
| joint_o4_e4_prior | 3 | 0.0041 |  | 0 |

## Split truth (f = 1.25; pull SD meaningful for interleaved only)

| method | variant | n | bias | pull SD |
|---|---|---|---|---|
| legacy | interleaved | 3 | 0.0026 | 3.27 |
| legacy | shared | 3 | -0.0000 | 2.53 |
| interp | interleaved | 3 | 0.0026 | 1.59 |
| interp | shared | 3 | 0.0000 | 0.00 |
| interp_log | interleaved | 3 | 0.0028 | 1.72 |
| interp_log | shared | 3 | -0.0000 | 0.00 |
| coincident | shared | 3 | 0.0000 | 0.00 |
| joint_o2_e0 | interleaved | 3 | 0.0051 | 1.80 |
| joint_o2_e0 | shared | 3 | 0.0000 | 0.00 |
| joint_o4_e2 | interleaved | 3 | 0.0034 | 1.46 |
| joint_o4_e2 | shared | 3 | 0.0002 | 0.20 |
| joint_o4_e4 | interleaved | 3 | 0.0039 | 1.30 |
| joint_o4_e4 | shared | 3 | 0.0001 | 0.12 |
| joint_o4_e4_raw | interleaved | 3 | 0.0038 | 1.31 |
| joint_o4_e4_raw | shared | 3 | 0.0001 | 0.10 |
| joint_o4_e4_log | interleaved | 3 | 0.0039 | 1.30 |
| joint_o4_e4_log | shared | 3 | 0.0001 | 0.12 |
