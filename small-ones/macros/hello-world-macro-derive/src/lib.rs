#![allow(unused_imports)]

// extern crate proc_macro;
// extern crate syn;
// #[macro_use]
// extern crate quote;

use std::{collections::HashMap};
use proc_macro::{TokenStream};
use quote::{ToTokens, quote};
// use syn::{Ident};
use syn::{Attribute, DeriveInput, parse_macro_input, Path, punctuated::Punctuated, Token};
use syn_unnamed_struct::{Meta};
use proc_macro2::{Ident, Span};

#[derive(Default)]
struct FieldArgs {
    pub string: bool,
    pub int: bool,
}

#[proc_macro_derive(HelloWorld, attributes(my_id, discriminator, account))]
pub fn derive_trait(input: TokenStream) -> TokenStream {
    let input = parse_macro_input!(input);
    let DeriveInput { ident, attrs, data, .. } = &input;

    let mut output = proc_macro2::TokenStream::new();
    
    let name = ident.clone();
    println!(">>>> name: {:?}", name);
    let expanded = quote! {
        impl HelloWorld for #name {
            fn hello_world() {
                println!("Hello, World! from {}", stringify!(#name));
            }
        }
    };
    output.extend(expanded);

    let sss: Ident = Ident::new("String",Span::call_site());
    let iii: Ident = Ident::new("u64",Span::call_site());
    let obj = match data {
        syn::Data::Struct(obj) => obj,
        _ => panic!("Only structs supported in From macro")
    };
    let attributes = obj.fields
        .iter()
        .map(|field| {
            let field_name = field.ident.as_ref().expect("Structs must contain named fields").clone();

            print!("field {:?} is type {:?}", field_name.to_token_stream().to_string(), field.ty.to_token_stream().to_string());
            match &field.ty {
                syn::Type::Array(_ty) => {println!("; is array")}
                syn::Type::BareFn(_ty) => {println!("; is bare fn")}
                syn::Type::Group(_ty) => {println!("; is group")}
                syn::Type::ImplTrait(_ty) => {println!("; is ImplTrait")}
                syn::Type::Infer(_ty) => {println!("; is Infer")}
                syn::Type::Macro(_ty) => {println!("; is Macro")}
                syn::Type::Never(_ty) => {println!("; is Never")}
                syn::Type::Paren(_ty) => {println!("; is Paren")}
                syn::Type::Path(_ty) => {println!("; is Path")}
                syn::Type::Ptr(_ty) => {println!("; is Ptr")}
                syn::Type::Reference(_ty) => {println!("; is Reference")}
                syn::Type::Slice(_ty) => {println!("; is Slice")}
                syn::Type::TraitObject(_ty) => {println!("; is TraitObject")}
                syn::Type::Tuple(_ty) => {println!("; is Tuple")}
                syn::Type::Verbatim(_ty) => {println!("; is verbatim")}
                #[cfg_attr(test, deny(non_exhaustive_omitted_patterns))]
                _ => { println!("; cannot find type of ty Type") }
            }

            let mut props = FieldArgs::default();
            field.attrs.iter().filter(|a| a.path.is_ident("account")).flat_map(|attr| {
                attr.parse_args_with(<Punctuated<Meta, Token![,]>>::parse_terminated).expect("Could not parse 'from' attribute")
            }).for_each(|meta| {
                match meta {
                    Meta::Path(path) => {
                        match path.to_token_stream().to_string().as_str() {
                            "string" => {
                                props.string = true;
                            },
                            "int" => {
                                props.int = true;
                            },
                            _ => panic!("Unrecognised attribute of field '{}'", field_name.to_string())
                        }
                    },
                    _ => panic!("Attribute for field {} contains urecognized value", field_name.to_string())
                }
            });

            (field_name,props)
        })
        .collect::<Vec<_>>();
    println!(">>>> Struct idents: {:?}", attributes.iter().map(|(i,_)| i).collect::<Vec<_>>());
    let quoted_fields = attributes.iter().map(|(name,ops)|{
        if ops.int {
            quote!(#name: #iii)
        } else {
            quote!(#name: #sss)
        }
    })
    .collect::<Vec<_>>();
    let struct_impl = quote! {
        #[derive(Debug)]
        struct OhMyGosh {
            #(#quoted_fields),*
        }
    };
    output.extend(struct_impl);

    // let type_names = attrs.iter().filter(|a| a.path.is_ident("discriminator")).flat_map(|attr| {
    //     attr.parse_args_with(Punctuated::<Path, Token![,]>::parse_terminated).expect("Could not parse 'discriminator' attribute")
    // }).map(|path| {
    //     (path.to_token_stream().to_string(), path)
    // }).collect::<HashMap<String, Path>>();
    // let n = type_names.iter().map(|(k,_)| {k}).collect::<Vec<_>>();
    // ---
    // println!(">>>> struct attributes: {:?}", n);
    // for i in 0..attrs.len() {
    //     if input.attrs[i].path.is_ident("discriminator") {
    //         let discriminator: &Attribute = input.attrs.get(i).unwrap();
    //         if discriminator.tokens.is_empty() {
    //             panic!("Failed to read discriminator data as have no data");
    //         }
    //         let tokens = discriminator.tokens.clone().into_iter();
    //         for data in tokens {
    //             brace_token: syn::braced!(content in input)
    //             let data_str: String = data.to_string();
    //             println!("next token: '{}'", data_str);
    //         }
    //     }
    // }

    let discriminator_attrs = attrs.iter().filter(|a| a.path.is_ident("discriminator"))
        // .flat_map(|attr| {attr.tokens.clone()}).collect::<Vec<_>>();
        .flat_map(|attr| {attr.tokens.clone()}).collect::<Vec<_>>();
    let discriminator_attr = discriminator_attrs.get(0).unwrap();
    let my_ids = attrs.iter().filter(|a| a.path.is_ident("my_id"))
        .flat_map(|attr|
            attr.parse_args_with(Punctuated::<Path, Token![,]>::parse_terminated).expect("Could not parse 'my_id' attribute")
        ).collect::<Vec<_>>();
    let my_id = my_ids.get(0).unwrap();
    let oh_my_gosh_impl = quote! {
        impl OhMyGosh {
            const DISCRIMINATOR:[u8;8] = #discriminator_attr;

            pub fn get_id() -> String {
                #my_id.to_string()
            }
        }
    };
    output.extend(oh_my_gosh_impl);

    output.into()
}


#[cfg(test)]
mod tests {
    #[test]
    fn it_works() {
        assert_eq!(42, 42);
    }
}
