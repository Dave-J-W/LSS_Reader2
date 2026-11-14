#directly after performing A
###Testing for Radiation Damage Before GID scans

def dppc_burn'
###For DPPC, 1st order peak at dth=16.5
######Setup GID Slits
absclose
umv dth 16.5
gid_slits_16
###dth scan do not need sleep
_sleep=0
###Burning test
umv dth 16.5
umv mabs 12
dscan ih 0 0 20 10
##plot the scan in Python
###Real Burning
umv dth 16.5
umv mabs 8
dscan ih 0 0 20 10

cleanup_sh
'
