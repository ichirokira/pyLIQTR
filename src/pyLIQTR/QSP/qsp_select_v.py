"""
DISTRIBUTION STATEMENT A. Approved for public release. Distribution is unlimited.

This material is based upon work supported by the Under Secretary of Defense for
Research and Engineering under Air Force Contract No. FA8702-15-D-0001. Any opinions,
findings, conclusions or recommendations expressed in this material are those of the
author(s) and do not necessarily reflect the views of the Under Secretary of Defense
for Research and Engineering.

© 2022 Massachusetts Institute of Technology.

The software/firmware is provided to you on an As-Is basis

Delivered to the U.S. Government with Unlimited Rights, as defined in DFARS Part
252.227-7013 or 7014 (Feb 2014). Notwithstanding any copyright notice, U.S. Government
rights in this work are defined by DFARS 252.227-7013 or DFARS 252.227-7014 as detailed
above. Use of this work other than as specifically authorized by the U.S. Government
may violate any copyrights that exist in this work.
"""

import cirq
import numpy as np

#toffoli with appropriate basis change gates
def toffoli(b0,b1,ctl0,ctl1,trgt):
        #3 qubits.
        basis_change = []
        if not b0:
            basis_change.append(cirq.X.on(ctl0))
        if not b1:
            basis_change.append(cirq.X.on(ctl1))
        
        cnX = cirq.X(trgt).controlled_by(ctl0,ctl1)

        return (basis_change+[cnX]+basis_change[::-1])

#implemented & checked
def walkDown(bTree, qubits, ancilla):
    def walkDown_helper(myc,bt,qbt,anc):
        if len(bt)==0:
            return myc
        else:
            myc.append(toffoli(bt[0],True, qbt[0], anc[0], anc[1]))
            myc = walkDown_helper(myc, bt[1::], qbt[1::], anc[1::])
            return myc
        
    circuit = cirq.Circuit()
    circuit.append(toffoli(bTree[0],bTree[1], qubits[0], qubits[1], ancilla[0]))
    circuit = walkDown_helper(circuit, bTree[2::], qubits[2::], ancilla)
    
    return circuit

#implemented
#given a binary, insert the gates required to move from one node to a node on the right
def stepRight(circuit, bTree, qubits, ancilla):
    def myTof(c1,c2,trgt):
        return toffoli(True,False,c1,c2,trgt)

    def nth2last(n):
        return -(n+1)
    def h_distance(val1,val2):
        return sum([0 if v1==v2 else 1 for v1,v2 in zip(val1,val2)])
    #particular tree traversal rules
    distance = h_distance(bTree,incrementBooleanTree(bTree))
    n_anc = len(ancilla)
    if distance == 0:
        pass #no need to do anything.
    elif distance == 1:
        if n_anc == 1:
            q0 = ancilla[nth2last(0)]
            circuit.append(cirq.X.on(q0))
        else:
            q0 = ancilla[nth2last(0)]
            q1 = ancilla[nth2last(1)]
            circuit.append(cirq.CX.on(q1,q0))
    elif distance == 2:
        if n_anc == 2:
            q0 = ancilla[nth2last(0)]
            q1 = ancilla[nth2last(1)]
            x0 = qubits[nth2last(0)]
            circuit.append(cirq.CX.on(q1,q0))
            circuit.append(cirq.CX.on(x0,q0))
            circuit.append(cirq.X.on(q1))
            circuit.append(cirq.X.on(q0))
        else:
            q0 = ancilla[nth2last(0)]
            q1 = ancilla[nth2last(1)]
            q2 = ancilla[nth2last(2)]
            x0 = qubits[nth2last(0)]
            circuit.append(cirq.CX.on(q1,q0))
            circuit.append(myTof(q2,x0,q0))
            circuit.append(cirq.CX.on(q2,q1))
    else:
        #recurse
        x0 = qubits[nth2last(0)]
        q0 = ancilla[nth2last(0)]
        q1 = ancilla[nth2last(1)]

        qubits2 = qubits[0:-1]
        ancilla2 = ancilla[0:-1]
        m_bTree = bTree[0:-1]
        circuit.append(toffoli(True, True, q1, x0, q0))
        circuit = stepRight(circuit, m_bTree, qubits2, ancilla2)
        circuit.append(toffoli(True, False, q1, x0, q0))
    
    return circuit

#implemented
def applyAndStep(operators, start_bTree, end_bTree, controls, ancilla, target):
    def applyAndStep_helper(myc, ops, sbT, ebT, qbs, anc, tgt):
        if sbT == ebT:
            myc.append(ops[0](anc[-1],tgt))
            return myc
        else:
            myc.append(ops[0](anc[-1],tgt))
            myc = stepRight(myc, sbT.copy(), qbs, anc)
            return applyAndStep_helper(myc, ops[1::], incrementBooleanTree(sbT),\
                            ebT, qbs, anc, tgt)

    circuit = cirq.Circuit()
    return applyAndStep_helper(circuit, operators, start_bTree, end_bTree,\
                     controls, ancilla, target)



#these two methods should just get wrapped into a class.
def constructBooleanTree(n,m):
    n = bin(n)[2:]
    value = ''.join([''.join(['0' for __ in range(m-len(n))]),n])
    value = [True if v=='1' else False for v in value ]
    return value

def incrementBooleanTree(n):
    def incBT(m):
        h = m[0]
        m = m[1::]
        if h == False:
            return [True] + m
        else:
            return [False] + incBT(m)
    n = n.copy()
    n.reverse()
    n = incBT(n)
    n.reverse()
    return n

# apply operators from Hamiltonian controlled on address bits using a QROM
#
def applyAndWalk(operators, pos1, pos2, ctl_q, sel_q, anc_q, tgt_q):

    # Generate a circuit that implements a QROM (based on construction in Fig. 2 of arXiv:1905.07682)
    # This circuit accepts a dictionary with (address,data) pairs for each uniquue entry
    # The bit-width of any address must be less than the specified bit-width, however,
    # all addresses do not need to be specified
    # The QROM works by iterating over the addresses in numeric order
    # A set of ancilla bits (b) are used to build up the current selected address from the address bits (a)
    # Each subsequent bit adds a bit of the selected address to the ancilla register
    # For example, if we have a 3-bit address then: (where a_i corresponds to the current value of the address)
    # b_2 = a_2
    # b_1 = a_2 ^ a_1
    # b_0 = a_2 ^ a_1 ^ a_0
    #
    # To set the current value, from a cleared ancilla register, we build it up one bit at a time
    # with a CCX gate per bit (the control is either zero or one controlled based on the value of the address bit)
    #
    # To move from one current address value to another there are three main operations:
    #      1) flipping the bit value of the current address (this is done as CX: b_i+1 -> b_i)
    #      2) clearing the current address (this is the inverse process of setting the value)
    #      3) setting a new value (this is the same as above)
    # This process of moving from one address to the next consists of three steps:
    #      1) Clearing the current address bits differ in only one position
    #      2) Flipping the bit that differs
    #      3) Setting the bits that were cleared to the new value
    #
    # Parameters:
    # qubit_dict - contains starting location of qubits
    # width - number of address bit in QROM
    # key_values - list of address values
    # operators - operators for each key
    #
    def qrom(qubit_dict, width, key_vals, operators):

        circuit = cirq.Circuit()
        circuit2 = cirq.Circuit()
        
        prev_key_val = -1
        addrQubits = qubit_dict['a'][::-1]   # address bits
        ancQubits = qubit_dict['b'][::-1]   # ancilla that holds current address
        selQubit = qubit_dict['s']   # global select
        trgtQubits = qubit_dict['t']   # target for memory

        for key_val in key_vals:
            if prev_key_val == -1:
                # special case for the first value, build up the initial set of ancilla
                for bi in range(width)[::-1]:
                    ctlSense = (key_val >> bi) % 2 == 1

                    # Extend the address starting from the MSB, the first gate is controlled on the global select
                    if bi+1 == width:
                        circuit.append(toffoli(True, ctlSense, selQubit , addrQubits[bi], ancQubits[bi]))
                    else:
                        circuit.append(toffoli(True, ctlSense, ancQubits[bi + 1] , addrQubits[bi], ancQubits[bi]))
                    
            else:
                # move from previous key value to the new key value
                ci = 0

                # clear the current address until we get to a state where the bit values are equal
                while not (prev_key_val >> (ci+1)) == (key_val >> (ci+1)):
                    ctlSense = (prev_key_val >> ci) % 2 == 1
                    circuit.append(toffoli(True, ctlSense, ancQubits[ci + 1], addrQubits[ci], ancQubits[ci]))

                    ci += 1

                # flip the address of the least signfificant bit that is different
                if (ci + 1) == width:
                    circuit.append(cirq.CX.on(selQubit, ancQubits[ci]))
                else:
                    circuit.append(cirq.CX.on(ancQubits[ci + 1], ancQubits[ci]))

                # work our way down to the new value
                while ci > 0:
                    ctlSense = (key_val >> (ci-1)) % 2 == 1
                    circuit.append(toffoli(True, ctlSense, ancQubits[ci], addrQubits[ci - 1], ancQubits[ci - 1]))
                    
                    ci -= 1

            # apply the operator
            circuit.append(operators[key_val](ancQubits[0], trgtQubits))
            
            prev_key_val = key_val

        # clear the ancilla register
        if not prev_key_val == -1:
            for ci in range(width):
                ctlSense = (prev_key_val >> ci) % 2 == 1

                if (ci + 1) == width:
                    circuit.append(toffoli(True, ctlSense, selQubit, addrQubits[ci], ancQubits[ci]))
                else:
                    circuit.append(toffoli(True, ctlSense, ancQubits[ci + 1], addrQubits[ci], ancQubits[ci]))

        return circuit

    qubit_dict = dict()
    qubit_dict['a'] = ctl_q
    qubit_dict['b'] = anc_q
    qubit_dict['s'] = sel_q
    qubit_dict['t'] = tgt_q
    
    key_values = [ii+pos1 for ii in range(pos2-pos1)]
    
    return qrom(qubit_dict, len(ctl_q), key_values, operators)

class SelVBase(cirq.Gate):
    #do we need knowledge of the hamiltonian here?
    def __init__(self,invert, hamiltonian,phase_qubit, target_qubits, control_qubits, ancilla_qubits,\
                    n_controls=2):
        self.__phs_q = phase_qubit
        self.__ctl_q = control_qubits
        self.__tgt_q = target_qubits
        self.__anc_q = ancilla_qubits
        self.__hamiltonian = hamiltonian

        super(SelVBase, self)
        
    def _num_qubits_(self):
        return len(self.__tgt_q)+len(self.__ctl_q)+1+len(self.__anc_q)

    def convert_hamiltonian_terms_to_operators(self):
        def controlled_pauli_gate(pauliString, ctrl, targets):
            gate_sequence = []
            for p,tq in zip(pauliString,targets):
                if p == "I":
                    continue
                elif p == "X":
                    gate_sequence.append(cirq.CX.on(ctrl,tq))
                elif p == "Y":
                    gate_sequence.append(cirq.inverse(cirq.S.on(tq)))
                    gate_sequence.append(cirq.CX.on(ctrl,tq))
                    gate_sequence.append(cirq.S.on(tq))
                elif p == "Z":
                    gate_sequence.append(cirq.CZ.on(ctrl,tq))

            return gate_sequence

        operator_generators = []
        for term in self.__hamiltonian.terms:
            if (term[1] < 0):
                add_z = lambda ctrl, qubits : [cirq.Z.on(ctrl)]
                gate_seq = lambda ctrl, qubits, pauli=term[0]: add_z(ctrl, qubits)+controlled_pauli_gate(pauli,ctrl,qubits)
                operator_generators.append(gate_seq)
            else:
                gate_seq = lambda ctrl, qubits, pauli=term[0]: controlled_pauli_gate(pauli,ctrl,qubits)
                operator_generators.append(gate_seq)
        return operator_generators

    def _decompose_(self, qubits):
        #this is selectV!
        #helper functions~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        #identify pos1 and pos2
        #need to map hamiltonian terms to operators
        ham_ps_is_identity = [(np.all([p=="I" for p in term[0]]) or term[1]==0) for term in self.__hamiltonian.terms]
        def find_first_non_identity_term(check):
            for idx,k in enumerate(check):
                if not k:
                    return idx    
        pos1 = find_first_non_identity_term(ham_ps_is_identity)
        pos2 = len(self.__hamiltonian) - find_first_non_identity_term(ham_ps_is_identity[::-1])
        #this travels a tree and implements the selectV as appropriate
        #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

        if True:
            # this is the new way to do SelectV
            ham_as_ops = self.convert_hamiltonian_terms_to_operators()
            circuit = applyAndWalk(ham_as_ops, pos1, pos2, self.__ctl_q, self.__phs_q, self.__anc_q, self.__tgt_q)
            yield circuit
        else:
            # this is the new way to do selectV
            ham_as_ops = self.convert_hamiltonian_terms_to_operators()[pos1::]
            start_node = [True]+constructBooleanTree(pos1,len(self.__ctl_q))
            end_node = [True]+constructBooleanTree(pos2-1,len(self.__ctl_q))

            downCircuit = walkDown(start_node, [self.__phs_q]+self.__ctl_q, self.__anc_q)
            applyCircuit = applyAndStep(ham_as_ops, start_node, end_node, \
                                        self.__ctl_q, [self.__phs_q]+self.__anc_q, self.__tgt_q)

            upCircuit =  cirq.inverse(walkDown(end_node, [self.__phs_q]+self.__ctl_q, self.__anc_q))

            yield downCircuit
            yield applyCircuit
            yield upCircuit

    def _circuit_diagram_info_(self, args):
        return ["SelVBase"] * self.num_qubits()
