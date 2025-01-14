"""
DISTRIBUTION STATEMENT A. Approved for public release. Distribution is unlimited.

This material is based upon work supported by the Under Secretary of Defense for
Research and Engineering under Air Force Contract No. FA8702-15-D-0001. Any opinions,
findings, conclusions or recommendations expressed in this material are those of the
author(s) and do not necessarily reflect the views of the Under Secretary of Defense
for Research and Engineering.

© 2023 Massachusetts Institute of Technology.

The software/firmware is provided to you on an As-Is basis

Delivered to the U.S. Government with Unlimited Rights, as defined in DFARS Part
252.227-7013 or 7014 (Feb 2014). Notwithstanding any copyright notice, U.S. Government
rights in this work are defined by DFARS 252.227-7013 or DFARS 252.227-7014 as detailed
above. Use of this work other than as specifically authorized by the U.S. Government
may violate any copyrights that exist in this work.
"""
from openfermion   import jordan_wigner
import numpy       as np
import openfermion as of


qasm_convert_one_qubit_gates = {
    'H': 'h',
    'X': 'x'
}

qasm_convert_rotation_gates = {
    'Rx': 'rx',
    'Ry': 'ry',
    'Rz': 'rz',
}

qasm_convert_two_qubit_gates = {
    'CNOT': 'cx'
}

def open_fermion_to_qasm(n_qubits:int, ofq_str, reg_name:str='reg', include_heading:bool=True):
    """
    A function for converting the openfermion qasm to OpenQASM 2.0

    Parameters:
        n_qubits : the number of qubits in the circuit

        ofq_str : trotterized qasm string generator (output of trotterise_exp_qubop_to_qasm)

        reg_name : The prefix name for the register qubits

        include_heading: Boolean, if you want to include the heading in the file

    Returns:
        str_out : a string containing the OpenQASM 2.0 circuit
    """
    if include_heading:
        str_out =  '// Generated from Cirq, Openfermion, and MIT LL\n\n'
        str_out += 'OPENQASM 2.0;\n'
        str_out += 'include \"qelib1.inc\";\n\n'
        str_out += f'qreg {reg_name}[{n_qubits}];\n\n'
    else:
        str_out = ''
        
    for moment_str in ofq_str:
        
        # split the string and grab the gate:
        gate = moment_str.split(' ')[0]
       
        if gate in qasm_convert_one_qubit_gates:
            
            qubit_id = int(moment_str.split(' ')[-1])
            str_out += f'{qasm_convert_one_qubit_gates[gate]} {reg_name}[{qubit_id}];\n'

        elif gate in qasm_convert_two_qubit_gates:
            
            qubit_ids = [int(x) for x in moment_str.split(' ')[1:]]
            str_out += f'{qasm_convert_two_qubit_gates[gate]} {reg_name}[{qubit_ids[0]}],{reg_name}[{qubit_ids[1]}];\n'

        elif gate in qasm_convert_rotation_gates:
            
            rotation = float(moment_str.split(' ')[1])/np.pi
            qubit_id = int(moment_str.split(' ')[-1])
            str_out += f'{qasm_convert_rotation_gates[gate]}(pi*{rotation}) {reg_name}[{qubit_id}];\n'
        else:
            print(f'> Gate = {gate} not in gate tables')
        
    
    return str_out

def count_T_gates(circuit):
    '''
    For counting the number of T-Gates in a circuit

    Parameters:
     - circuit: The circuit to count T-Gates in

    Returns:
     - T_gate_counter: the number of T-Gates in the circuit

    '''
    T_gate_counter = 0
        
    for moment in circuit:
        for op in moment:
            if (str(op).startswith('T')):
                T_gate_counter += 1

    return (T_gate_counter)