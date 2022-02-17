use borsh::{BorshDeserialize, BorshSerialize};

/// Define the type of state stored in accounts
#[derive(BorshSerialize, BorshDeserialize, Debug)]
pub struct ChkpCounterAccount {
    pub counter: u32,
    pub timestamp: i64,
}

pub enum InstructionTypes {
    Unknown = 0,
    Counter = 1,
    DeletePda = 2
}

pub fn parse_instruction(input: &[u8]) -> (InstructionTypes, &[u8]) {
    let parsed_first_byte = input.split_first();

    let (itype, rest) = match parsed_first_byte {
        Some((instruction_type, rest)) => (*instruction_type as u8, rest),
        None                           => (0, input),
    };

    let instruction_type = match itype {
        1 => InstructionTypes::Counter,
        2 => InstructionTypes::DeletePda,
        _ => InstructionTypes::Unknown,
    };
    (instruction_type, rest)
}