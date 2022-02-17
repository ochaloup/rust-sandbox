use solana_program::{
    account_info::{next_account_info, AccountInfo},
    entrypoint::ProgramResult,
    msg,
    program_error::ProgramError,
    pubkey::Pubkey,
};
use borsh::{BorshDeserialize, BorshSerialize};

use crate::{instructions::ChkpCounterAccount};

pub struct Processor;
impl Processor {
    pub fn process(
        program_id: &Pubkey,
        accounts: &[AccountInfo],
        _instruction_data: &[u8],
    ) -> ProgramResult {
        Self::process_greetings(program_id, accounts)
    }

    // Greetings
    pub fn process_greetings(
        program_id: &Pubkey, // Public key of the account the hello world program was loaded into
        accounts: &[AccountInfo], // The account to say hello to
    ) -> ProgramResult {
        msg!("Hello World Rust program entrypoint");
        // Iterating accounts is safer than indexing
        let accounts_iter = &mut accounts.iter();

        // Get the account to say hello to
        let data_account = next_account_info(accounts_iter)?;
        // The account must be owned by the program in order to modify its data
        if data_account.owner != program_id {
            msg!("Greeted account does not have the correct program id");
            return Err(ProgramError::IncorrectProgramId);
        }
        msg!("Hello World owner: {}, {}", data_account.owner, program_id);

        let signer_account = next_account_info(accounts_iter)?;
        if data_account.owner != signer_account.key || !signer_account.is_signer {
            msg!("Data account owner has to sign the transaction");
            return Err(ProgramError::IllegalOwner);
        }

        // Increment and store the number of times the account has been greeted
        let mut greeting_account = ChkpCounterAccount::try_from_slice(&data_account.data.borrow())?;
        greeting_account.counter += 1;
        greeting_account.serialize(&mut &mut data_account.data.borrow_mut()[..])?;

        msg!("Greeted {} time(s)!", greeting_account.counter);

        Ok(())
    }
}

// Sanity tests
#[cfg(test)]
mod test {
    use super::*;
    use solana_program::clock::Epoch;
    use std::mem;
    use Processor;

    #[test]
    fn test_sanity() {
        let program_id = Pubkey::default();
        let key = Pubkey::default();
        let mut lamports = 0;
        let mut data = vec![0; mem::size_of::<u32>()];
        let owner = Pubkey::default();
        let program_owner = Pubkey::default();
        let data_account = AccountInfo::new(
            &key,
            false,
            true,
            &mut lamports,
            &mut data,
            &owner,
            false,
            Epoch::default(),
        );
        let mut lamports_program = 0;
        let mut data_program = vec![];
        let program_account = AccountInfo::new(
            &owner,
            true,
            true,
            &mut lamports_program,
            &mut data_program,
            &program_owner,
            false,
            Epoch::default(),
        );
        // let instruction_data: Vec<u8> = Vec::new();

        let accounts = vec![data_account, program_account];

        assert_eq!(
            ChkpCounterAccount::try_from_slice(&accounts[0].data.borrow())
                .unwrap()
                .counter,
            0
        );
        Processor::process_greetings(&program_id, &accounts).unwrap();
        assert_eq!(
            ChkpCounterAccount::try_from_slice(&accounts[0].data.borrow())
                .unwrap()
                .counter,
            1
        );
        Processor::process_greetings(&program_id, &accounts).unwrap();
        assert_eq!(
            ChkpCounterAccount::try_from_slice(&accounts[0].data.borrow())
                .unwrap()
                .counter,
            2
        );
    }
}