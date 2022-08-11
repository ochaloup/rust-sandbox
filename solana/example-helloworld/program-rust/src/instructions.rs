use borsh::{BorshDeserialize, BorshSerialize};

/// Define the type of state stored in accounts
#[derive(BorshSerialize, BorshDeserialize, Debug)]
pub struct TestCounterAccount {
    pub counter: u32,
    pub timestamp: i64,
    pub client_timestamp: i64,
}

#[derive(Debug)]
pub enum InstructionTypes {
    Unknown = 0,

    /// Accounts expected by this instruction (2):
    /// 0. `[writable]` program_data - address where data is stored
    /// 1. `[]` program - account owning the program_data which has to sign the transaction 
    Counter = 1,

    /// Accounts expected by this instruction (3):
    /// 0. `[writable]` program_data - address where data is stored
    /// 1. `[]` program - account owning the program_data which has to sign the transaction
    /// 3. `[]` transfer_account - account where the SOL from program_data account will be transfered to
    DeleteAccount = 2
}

pub fn parse_instruction(input: &[u8]) -> (InstructionTypes, &[u8]) {
    let parsed_first_byte = input.split_first();

    let (itype, rest) = match parsed_first_byte {
        Some((instruction_type, rest)) => (*instruction_type as u8, rest),
        None                           => (0, input),
    };

    let instruction_type = match itype {
        1 => InstructionTypes::Counter,
        2 => InstructionTypes::DeleteAccount,
        _ => InstructionTypes::Unknown,
    };
    (instruction_type, rest)
}