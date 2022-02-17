use solana_program::{
    account_info::{next_account_info, AccountInfo},
    entrypoint::ProgramResult,
    msg,
    program_error::ProgramError,
    pubkey::Pubkey,
    sysvar::{
        clock::Clock, Sysvar,
    },
};
use borsh::{BorshDeserialize, BorshSerialize};

use crate::{
    instructions::{ChkpCounterAccount, parse_instruction, InstructionTypes},
    errors::ChkpCounterError::{InvalidInstruction}
};

pub struct Processor;
impl Processor {
    pub fn process(
        program_id: &Pubkey,
        accounts: &[AccountInfo],
        instruction_data: &[u8],
    ) -> ProgramResult {
        let (instruction_type, _rest_data) = parse_instruction(instruction_data);
        return match instruction_type {
            InstructionTypes::Counter => Self::process_counter(program_id, accounts),
            InstructionTypes::DeletePda => Self::process_delete_pda(program_id, accounts),
            _ => Err(InvalidInstruction.into())
        };
    }

    pub fn verify_program_owner(program_id: &Pubkey, accounts: &[AccountInfo]) -> Result<(),ProgramError> {
        // Iterating accounts (safer than indexing)
        let accounts_iter = &mut accounts.iter();

        // Get the data account
        let data_account = next_account_info(accounts_iter)?;
        msg!("Pubkeys: {}, {}", data_account.owner, program_id);  // TODO: DELETE ME
        // The account must be owned by the program in order to modify its data
        if data_account.owner != program_id {
            msg!("Greeted account does not have the correct program id");
            return Err(ProgramError::IncorrectProgramId);
        }

        let signer_account = next_account_info(accounts_iter)?;
        // The owner of the data account has to sign the transaction
        if data_account.owner != signer_account.key || !signer_account.is_signer {
            msg!("Data account owner has to sign the transaction");
            return Err(ProgramError::IllegalOwner);
        }
        Ok(())
    }

    pub fn process_counter(
        program_id: &Pubkey, // Public key of this program
        accounts: &[AccountInfo], // The PDA account where the data is saved
    ) -> ProgramResult {
        Self::verify_program_owner(program_id, accounts)?;

        let accounts_iter = &mut accounts.iter();
        let data_account = next_account_info(accounts_iter)?;

        // Increment and store the number of times the account has been greeted
        let mut greeting_account = ChkpCounterAccount::try_from_slice(&data_account.data.borrow())?;
        greeting_account.counter += 1;
        let clock = Clock::get();
        let timestamp = match clock {
            Ok(clock) => clock.unix_timestamp,
            Err(err) => {
                msg!("Error on using Sysvar Clock {}", err);
                -1
            }
        };
        greeting_account.timestamp = timestamp;
        greeting_account.serialize(&mut &mut data_account.data.borrow_mut()[..])?;

        msg!("Greeted {} time(s)!", greeting_account.counter);

        Ok(())
    }

    pub fn process_delete_pda(_program_id: &Pubkey, _accounts: &[AccountInfo]) -> ProgramResult {
        Ok(())
    }

    // pub fn process_delete_pda() -> None {
    //     msg!("Closing the escrow account...");
    //     **initializers_main_account.lamports.borrow_mut() = initializers_main_account.lamports()
    //     .checked_add(escrow_account.lamports())
    //     .ok_or(EscrowError::AmountOverflow)?;
    //     **escrow_account.lamports.borrow_mut() = 0;
    //     *escrow_account.try_borrow_mut_data()? = &mut [];

    //     Ok(())

    // }
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
        let data_pubkey = Pubkey::new_unique();
        let program_pubkey = Pubkey::new_unique();
        let mut lamports = 0;
        let mut data = vec![0; mem::size_of::<u32>() + mem::size_of::<i64>()];
        let data_account = AccountInfo::new(
            &data_pubkey,
            false,
            true,
            &mut lamports,
            &mut data,
            &program_pubkey,
            false,
            Epoch::default(),
        );
        let program_owner = Pubkey::default();
        let mut lamports_program = 0;
        let mut data_program = vec![];
        let program_account = AccountInfo::new(
            &program_pubkey,
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

        let account = ChkpCounterAccount::try_from_slice(&accounts[0].data.borrow()).unwrap();
        assert_eq!(account.counter, 0);
        assert_eq!(account.timestamp, 0);

        Processor::process_counter(&program_pubkey, &accounts).unwrap();
        let account = ChkpCounterAccount::try_from_slice(&accounts[0].data.borrow()).unwrap();
        assert_eq!(account.counter, 1);
        assert_eq!(account.timestamp, -1);

        Processor::process_counter(&program_pubkey, &accounts).unwrap();
        let account = ChkpCounterAccount::try_from_slice(&accounts[0].data.borrow()).unwrap();
        assert_eq!(account.counter, 2);
        assert_eq!(account.timestamp, -1);


        let instruction_data = vec![0];
        let error = Processor::process(&program_pubkey, &accounts, &instruction_data);
        assert_eq!(error, Err(InvalidInstruction.into()));

        let instruction_data = vec![1];
        Processor::process(&program_pubkey, &accounts, &instruction_data).unwrap();
        let account = ChkpCounterAccount::try_from_slice(&accounts[0].data.borrow()).unwrap();
        assert_eq!(account.counter, 3);
        assert_eq!(account.timestamp, -1);
    }
}